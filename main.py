import random
import asyncio
from typing import List, Optional, Tuple
from urllib.parse import urlparse
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx
from proxy_config import MIRRORS, HEALTH_CHECK_INTERVAL, HEALTH_CHECK_PATH

app = FastAPI(title="Docker Mirror Proxy")

healthy_mirrors: List[str] = MIRRORS.copy()
health_lock = asyncio.Lock()


async def check_mirror_health(mirror: str, client: httpx.AsyncClient) -> bool:
    try:
        url = f"{mirror.rstrip('/')}/{HEALTH_CHECK_PATH.lstrip('/')}"
        response = await client.get(url, timeout=5.0)
        return response.is_success
    except Exception:
        return False


async def periodic_health_check():
    async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
        while True:
            results = await asyncio.gather(
                *[check_mirror_health(mirror, client) for mirror in MIRRORS]
            )
            async with health_lock:
                healthy_mirrors.clear()
                for mirror, is_healthy in zip(MIRRORS, results):
                    if is_healthy:
                        healthy_mirrors.append(mirror)
            print(f"Healthy mirrors: {healthy_mirrors}")
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)


@app.on_event("startup")
async def startup():
    async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
        results = await asyncio.gather(
            *[check_mirror_health(mirror, client) for mirror in MIRRORS]
        )
        async with health_lock:
            healthy_mirrors.clear()
            for mirror, is_healthy in zip(MIRRORS, results):
                if is_healthy:
                    healthy_mirrors.append(mirror)
        print(f"Initial healthy mirrors: {healthy_mirrors}")
    asyncio.create_task(periodic_health_check())


async def get_healthy_mirror() -> Optional[str]:
    async with health_lock:
        if not healthy_mirrors:
            return None
        return random.choice(healthy_mirrors)


def parse_range_header(range_header: str) -> Optional[Tuple[int, Optional[int]]]:
    if not range_header or not range_header.startswith("bytes="):
        return None
    parts = range_header[6:].split("-")
    if len(parts) != 2:
        return None
    try:
        start = int(parts[0])
        end = int(parts[1]) if parts[1] else None
        return start, end
    except ValueError:
        return None


@app.api_route("/{path:path}", methods=["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    mirror = await get_healthy_mirror()
    if mirror is None:
        return Response(content="No healthy mirror available", status_code=503, media_type="text/plain")

    if not path.startswith("v2/"):
        return Response(content="Docker Registry API must start with /v2/", status_code=404, media_type="text/plain")

    clean_mirror = mirror.rstrip('/')
    clean_path = path if path.startswith('/') else f"/{path}"
    target_url = f"{clean_mirror}/{clean_path.lstrip('/')}"
    if request.url.query:
        target_url += f"?{request.url.query}"

    # آماده‌سازی هدرها
    headers = dict(request.headers)
    parsed_mirror = urlparse(mirror)
    host_header = parsed_mirror.hostname
    if parsed_mirror.port:
        host_header += f":{parsed_mirror.port}"
    headers["host"] = host_header
    headers.pop("connection", None)
    headers.pop("transfer-encoding", None)
    headers.pop("accept-encoding", None)
    for header in list(headers.keys()):
        if header.lower().startswith("x-"):
            del headers[header]

    # مدیریت هدر Range
    range_header = headers.pop("range", None)
    parsed_range = parse_range_header(range_header) if range_header else None
    original_range = range_header

    print(f"[*] Proxying: {request.method} {target_url}" +
          (f" (Range: {original_range})" if original_range else ""))

    try:
        limits = httpx.Limits(max_connections=10, max_keepalive_connections=0, keepalive_expiry=0)
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, read=120.0), limits=limits, verify=False) as client:
            body = await request.body()
            # ارسال Range به mirror اگر وجود داشته باشد
            if original_range:
                headers["range"] = original_range

            req = client.build_request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body if body else None,
            )
            resp = await client.send(req, stream=True)

            if resp.status_code >= 400:
                error_body = await resp.aread()
                print(f"[ERROR] Mirror returned {resp.status_code}: {error_body.decode('utf-8', errors='ignore')}")
                return Response(content=error_body, status_code=resp.status_code, headers=dict(resp.headers))

            # حالت 1: خود mirror 206 برگرداند -> عبور مستقیم
            if resp.status_code == 206:
                resp_headers = dict(resp.headers)
                resp_headers.pop("transfer-encoding", None)
                resp_headers.pop("connection", None)

                async def stream_206():
                    try:
                        async for chunk in resp.aiter_bytes():
                            yield chunk
                    except httpx.ReadError as e:
                        print(f"[STREAM_READ_ERROR] {e}")
                    except Exception as e:
                        print(f"[STREAM_ERROR] {e}")
                    finally:
                        await resp.aclose()

                return StreamingResponse(content=stream_206(), status_code=206, headers=resp_headers)

            # حالت 2: mirror 200 برگرداند ولی ما Range خواسته بودیم -> خودمان 206 خواسته بودیم -> خودمان 206 می‌سازیم
            if parsed_range and resp.status_code == 200:
                total_length = resp.headers.get("content-length")
                if total_length is None:
                    # اگر mirror Content-Length ندهد، مجبوریم کل محتوا را بخوانیم
                    print("[WARN] No Content-Length from mirror, reading entire body to create 206")
                    full_body = await resp.aread()  # خواندن کامل بدنه (ممکن است حافظه زیادی بگیرد)
                    total = len(full_body)
                else:
                    total = int(total_length)

                start = parsed_range[0]
                end = parsed_range[1] if parsed_range[1] is not None else total - 1

                # بررسی معتبر بودن محدوده
                if start >= total:
                    return Response(content="Range not satisfiable", status_code=416, media_type="text/plain")

                end = min(end, total - 1)
                content_length = end - start + 1

                # آماده‌سازی هدرهای پاسخ
                resp_headers = dict(resp.headers)
                resp_headers.pop("transfer-encoding", None)
                resp_headers.pop("connection", None)
                resp_headers["content-range"] = f"bytes {start}-{end}/{total}"
                resp_headers["content-length"] = str(content_length)
                # حذف هدر status اگر وجود دارد
                resp_headers.pop("status", None)

                if total_length is None:
                    # بدنه کامل در حافظه است -> برش داده و به عنوان Response برگردان
                    part = full_body[start:start+content_length]
                    # اطمینان از بسته شدن resp (اگر هستند)
                    await resp.aclose()
                    return Response(
                        content=part,
                        status_code=206,
                        headers=resp_headers,
                        media_type=resp.headers.get("content-type"),
                    )
                else:
                    # از Content-Length استفاده می‌کنیم و بدنه را به صورت استریم برش می‌دهیم
                    async def stream_range():
                        try:
                            bytes_skipped = 0
                            remaining = content_length
                            async for chunk in resp.aiter_bytes():
                                chunk_len = len(chunk)
                                # اگر کل این chunk قبل از start است، ردش کن
                                if bytes_skipped + chunk_len <= start:
                                    bytes_skipped += chunk_len
                                    continue
                                # محاسبه offset داخل این chunk برای شروع
                                offset_in_chunk = max(0, start - bytes_skipped)
                                usable = chunk[offset_in_chunk:]
                                if len(usable) > remaining:
                                    usable = usable[:remaining]
                                yield usable
                                remaining -= len(usable)
                                bytes_skipped += chunk_len
                                if remaining <= 0:
                                    break
                        except Exception as e:
                            print(f"[RANGE STREAM ERROR] {e}")
                        finally:
                            await resp.aclose()

                    return StreamingResponse(
                        content=stream_range(),
                        status_code=206,
                        headers=resp_headers,
                        media_type=resp.headers.get("content-type"),
                    )

            # حالت 3: درخواست عادی (بدون Range) یا mirror مستقیماً 206 داده
            # (مربوط به حالتی است که mirror 206 داده بود قبلاً handle شده)
            # برای حالت عادی که range ندارد یا mirror فقط 200 برگردانده
            resp_headers = dict(resp.headers)
            resp_headers.pop("transfer-encoding", None)
            resp_headers.pop("connection", None)

            async def stream_normal():
                try:
                    async for chunk in resp.aiter_bytes():
                        yield chunk
                except httpx.ReadError as e:
                    print(f"[STREAM ERROR] {e}")
                finally:
                    await resp.aclose()

            return StreamingResponse(
                content=stream_normal(),
                status_code=resp.status_code,
                headers=resp_headers,
            )

    except httpx.ReadTimeout as e:
        print(f"[TIMEOUT] {path}: {e}")
        return Response(content="Upstream mirror timed out", status_code=504, media_type="text/plain")
    except RuntimeError as e:
        print(f"[STREAM ERROR] {path}: {e}")
        return Response(content=f"Stream error: {e}", status_code=502, media_type="text/plain")
    except Exception as e:
        print(f"[PROXY ERROR] {path}: {e}")
        return Response(content=f"Proxy error: {str(e)}", status_code=502, media_type="text/plain")
