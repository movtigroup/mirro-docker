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

    # فقط مسیرهای v2/ را قبول می‌کنیم
    if not path.startswith("v2/"):
        return Response(
            content="Docker Registry API must start with /v2/",
            status_code=404,
            media_type="text/plain",
        )

    # ساخت URL مقصد
    clean_mirror = mirror.rstrip('/')
    clean_path = path if path.startswith('/') else f"/{path}"
    target_url = f"{clean_mirror}{clean_path}"

    if request.url.query:
        target_url += f"?{request.url.query}"

    # کپی هدرهای اصلی
    headers = dict(request.headers)

    # تنظیم هدر Host مطابق آدرس mirror
    parsed_mirror = urlparse(mirror)
    host_header = parsed_mirror.hostname
    if parsed_mirror.port:
        host_header += f":{parsed_mirror.port}"
    headers["host"] = host_header

    # حذف هدرهایی که ممکن است مشکل ایجاد کنند
    headers.pop("connection", None)
    headers.pop("transfer-encoding", None)
    headers.pop("accept-encoding", None)

    # *** حذف هدرهای اضافی که توسط پروکسی بالادست اضافه می‌شوند ***
    for header in list(headers.keys()):
        if header.lower().startswith("x-forwarded-"):
            del headers[header]
    # همچنین حذف هدر docker-distribution-api-version که خودمان اضافه کرده بودیم
    # (mirror بدون آن کار می‌کند و شاید باعث 400 شود)
    headers.pop("docker-distribution-api-version", None)

    # لاگ درخواست برای دیباگ
    print(f"\n[PROXY] {request.method} {target_url}")
    print(f"[HEADERS] {dict(headers)}")

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

            # اگر پاسخ خطا بود، آن را چاپ و برگردان
            if resp.status_code >= 400:
                error_body = await resp.aread()
                print(f"[ERROR] Mirror returned {resp.status_code}: {error_body.decode('utf-8', errors='ignore')}")
                return Response(
                    content=error_body,
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                )

            # پاسخ موفق به صورت stream
            resp_headers = dict(resp.headers)
            resp_headers.pop("transfer-encoding", None)
            resp_headers.pop("connection", None)

            return StreamingResponse(
                content=resp.aiter_bytes(),
                status_code=resp.status_code,
                headers=resp_headers,
            )
    except Exception as e:
        print(f"[PROXY ERROR] {path}: {e}")
        return Response(
            content=f"Proxy error: {str(e)}",
            status_code=502,
            media_type="text/plain",
        )
