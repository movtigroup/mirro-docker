# main.py - Version with all fixes
import random
import asyncio
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx

from proxy_config import MIRRORS, HEALTH_CHECK_INTERVAL, HEALTH_CHECK_PATH

app = FastAPI(title="Docker Mirror Proxy")

healthy_mirrors: List[str] = []
health_lock = asyncio.Lock()

# تمام هدرهایی که توسط پروکسی بالادست (Nginx, Cloudflare, ...) اضافه می‌شوند
UPSTREAM_HEADERS = {
    "x-real-ip", "x-forwarded-for", "x-forwarded-proto", "x-forwarded-port",
    "x-forwarded-host", "x-forwarded-server", "x-forwarded-ssl", "x-forwarded-scheme",
    "x-nginx-proxy", "x-request-id", "x-trace-id", "cf-connecting-ip", "cf-ray",
    "cf-visitor", "cdn-loop", "true-client-ip", "x-amzn-trace-id"
}

async def check_mirror_health(mirror: str, client: httpx.AsyncClient) -> bool:
    try:
        url = f"{mirror.rstrip('/')}/{HEALTH_CHECK_PATH.lstrip('/')}"
        response = await client.get(url, timeout=5.0)
        return response.is_success
    except Exception:
        return False

async def periodic_health_check():
    async with httpx.AsyncClient(timeout=10.0) as client:
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
    asyncio.create_task(periodic_health_check())

async def get_healthy_mirror() -> Optional[str]:
    async with health_lock:
        if not healthy_mirrors:
            return None
        return random.choice(healthy_mirrors)

@app.api_route("/{path:path}", methods=["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    mirror = await get_healthy_mirror()

    if mirror is None:
        return Response(
            content="No healthy mirror available",
            status_code=503,
            media_type="text/plain",
        )

    if not path.startswith("v2/"):
        return Response(
            content="Docker Registry API must start with /v2/",
            status_code=404,
            media_type="text/plain",
        )

    clean_mirror = mirror.rstrip('/')
    clean_path = path if path.startswith('/') else f"/{path}"
    target_url = f"{clean_mirror}{clean_path}"

    if request.url.query:
        target_url += f"?{request.url.query}"

    headers = dict(request.headers)

    # تنظیم Host به آدرس mirror
    parsed_mirror = urlparse(mirror)
    host_header = parsed_mirror.hostname
    if parsed_mirror.port:
        host_header += f":{parsed_mirror.port}"
    headers["host"] = host_header

    # حذف هدرهای غیرضروری
    headers.pop("connection", None)
    headers.pop("transfer-encoding", None)
    headers.pop("accept-encoding", None)

    # حذف تمام هدرهای اضافی که توسط proxy بالادست افزوده شده‌اند (x-*)
    for header in list(headers.keys()):
        if header.lower().startswith("x-"):
            del headers[header]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            body = await request.body()
            req = client.build_request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body if body else None,
            )
            resp = await client.send(req, stream=True)

            if resp.status_code >= 400:
                # در صورت خطا، بدنه را بخوان و برگردان
                error_body = await resp.aread()
                print(f"[ERROR] Mirror returned {resp.status_code}: {error_body.decode('utf-8', errors='ignore')}")
                return Response(
                    content=error_body,
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                )

            # پاسخ موفق – stream با مدیریت خطا
            resp_headers = dict(resp.headers)
            resp_headers.pop("transfer-encoding", None)
            resp_headers.pop("connection", None)

            async def stream_generator():
                try:
                    async for chunk in resp.aiter_bytes():
                        yield chunk
                except httpx.ReadError as e:
                    # خطای خواندن معمولاً در حین دانلود لایه‌های بزرگ رخ می‌دهد
                    # client docker خودش درخواست را دوباره می‌فرستد (Range header)
                    print(f"[STREAM_READ_ERROR] {e}")
                except Exception as e:
                    print(f"[STREAM_UNEXPECTED_ERROR] {e}")

            return StreamingResponse(
                content=stream_generator(),
                status_code=resp.status_code,
                headers=resp_headers,
            )
    except httpx.ReadTimeout as e:
        print(f"[PROXY TIMEOUT] {path}: {e}")
        return Response(
            content="Upstream mirror timed out",
            status_code=504,
            media_type="text/plain",
        )
    except Exception as e:
        print(f"[PROXY ERROR] {path}: {e}")
        return Response(
            content=f"Proxy error: {str(e)}",
            status_code=502,
            media_type="text/plain",
        )
