import random
import asyncio
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx

from proxy_config import MIRRORS, HEALTH_CHECK_INTERVAL, HEALTH_CHECK_PATH

app = FastAPI(title="Docker Mirror Proxy")

# وضعیت سلامت میرورها
healthy_mirrors: List[str] = []  # آدرس میرورهای سالم
health_lock = asyncio.Lock()    # برای دسترسی هم‌زمان به لیست


async def check_mirror_health(mirror: str, client: httpx.AsyncClient) -> bool:
    """
    یک میرور را با فرستادن درخواست GET به HEALTH_CHECK_PATH بررسی می‌کند.
    """
    try:
        url = f"{mirror.rstrip('/')}/{HEALTH_CHECK_PATH.lstrip('/')}"
        response = await client.get(url, timeout=5.0)
        return response.is_success
    except Exception:
        return False


async def periodic_health_check():
    """بررسی دوره‌ای سلامت همه میرورها و به‌روزرسانی لیست سالم‌ها"""
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
    """شروع Health Check در background بعد از بالا آمدن اپ"""
    asyncio.create_task(periodic_health_check())


async def get_healthy_mirror() -> Optional[str]:
    """یک میرور سالم به صورت تصادفی برمی‌گرداند"""
    async with health_lock:
        if not healthy_mirrors:
            return None
        return random.choice(healthy_mirrors)


@app.api_route("/{path:path}", methods=["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    """
    تمام درخواست‌ها را دریافت کرده و به یک میرور سالم پراکسی می‌کند.
    """
    mirror = await get_healthy_mirror()
    
    if mirror is None:
        return Response(
            content="No healthy mirror available",
            status_code=503,
            media_type="text/plain",
        )

    # فقط مسیرهایی که با v2/ شروع می‌شوند را پردازش می‌کنیم
    if not path.startswith("v2/"):
        return Response(
            content="Docker Registry API must start with /v2/",
            status_code=404,
            media_type="text/plain",
        )

    # ساختن URL هدف
    clean_mirror = mirror.rstrip('/')
    clean_path = path if path.startswith('/') else f"/{path}"
    target_url = f"{clean_mirror}{clean_path}"
    
    if request.url.query:
        target_url += f"?{request.url.query}"

    # کپی هدرها و اصلاح آنها
    headers = dict(request.headers)
    
    # تنظیم هدر Host به آدرس میرور (mirror پاسخ درست می‌دهد)
    parsed_mirror = urlparse(mirror)
    host_header = parsed_mirror.hostname
    if parsed_mirror.port:
        host_header += f":{parsed_mirror.port}"
    headers["host"] = host_header
    
    # حذف هدرهایی که ممکن است باعث ایجاد مشکل شوند
    headers.pop("connection", None)
    headers.pop("transfer-encoding", None)
    headers.pop("accept-encoding", None)   # httpx خودش این را مدیریت می‌کند
    
    # اضافه کردن User-Agent پیش‌فرض
    headers.setdefault("user-agent", "Docker-Proxy/1.0")
    
    # برخی رجیستری‌ها نیاز به این هدر دارند
    headers.setdefault("docker-distribution-api-version", "registry/2.0")
    
    # اگر Accept وجود ندارد، مقدار پیش‌فرض را بگذارید
    headers.setdefault("accept", "*/*")

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
            
            # لاگ پاسخ mirror
            if resp.status_code >= 400:
                error_body = await resp.aread()
                print(f"[ERROR] Mirror returned {resp.status_code}: {error_body.decode('utf-8', errors='ignore')}")
                return Response(
                    content=error_body,
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                )

            # برگرداندن پاسخ موفق به صورت stream
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
