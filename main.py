import random
import asyncio
from typing import List, Optional
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

@app.api_route("/{path:path}", methods=["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    mirror = await get_healthy_mirror()
    
    if mirror is None:
        return Response(content="No healthy mirror available", status_code=503, media_type="text/plain")

    if not path.startswith("v2/"):
        return Response(content="Docker Registry API must start with /v2/", status_code=404, media_type="text/plain")

    # *** نکته کلیدی: پروتکل درخواست ورودی را حفظ کن ***
    # اگر کاربر https://armigram... را زده، ما هم https://mirror... را صدا می‌زنیم
    # اگر کاربر http://armigram... را زده، ما هم http://mirror... را صدا می‌زنیم
    request_scheme = request.url.scheme
    
    clean_mirror = mirror.rstrip('/')
    clean_path = path if path.startswith('/') else f"/{path}"
    
    # ساخت URL هدف با حفظ پروتکل ورودی
    target_url = f"{request_scheme}://{clean_mirror}{clean_path}"
    
    if request.url.query:
        target_url += f"?{request.url.query}"

    # کپی هدرها
    headers = dict(request.headers)
    
    # *** تنظیم هدر Host ***
    # مهم: هدر Host باید همان دامنه‌ای باشد که Docker می‌خواهد با آن صحبت کند.
    # اگر میرور arvancloud.ir است، هدر Host باید arvancloud.ir باشد.
    parsed_mirror = urlparse(mirror)
    host_header = parsed_mirror.hostname
    if parsed_mirror.port:
        host_header += f":{parsed_mirror.port}"
    headers["host"] = host_header
    
    # حذف هدرهای مزاحم که باعث 400 Bad Request می‌شوند
    headers.pop("connection", None)
    headers.pop("transfer-encoding", None)
    headers.pop("accept-encoding", None)
    # حذف هدرهای x-*
    for header in list(headers.keys()):
        if header.lower().startswith("x-"):
            del headers[header]

    print(f"[*] Proxying: {request.method} {target_url}")

    try:
        limits = httpx.Limits(
            max_connections=10,
            max_keepalive_connections=0,
            keepalive_expiry=0
        )
        
        # verify=False برای عبور از خطاهای SSL میرورهای داخلی
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, read=120.0),
            limits=limits,
            verify=False
        ) as client:
            body = await request.body()
            
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
                return Response(
                    content=error_body,
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                )

            resp_headers = dict(resp.headers)
            resp_headers.pop("transfer-encoding", None)
            resp_headers.pop("connection", None)

            async def stream_generator():
                try:
                    async for chunk in resp.aiter_bytes():
                        yield chunk
                except httpx.ReadError as e:
                    raise RuntimeError(f"Upstream read error: {e}")
                except Exception as e:
                    raise RuntimeError(f"Stream error: {e}")
                finally:
                    await resp.aclose()

            return StreamingResponse(
                content=stream_generator(),
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
