import random
import asyncio
from typing import List, Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx

from proxy_config import MIRRORS, HEALTH_CHECK_INTERVAL, HEALTH_CHECK_PATH

app = FastAPI(title="Docker Mirror Proxy")

# وضعیت سلامت میرورها
healthy_mirrors: List[str] = []  # آدرس میرورهای سالم
health_lock = asyncio.Lock()    # برای دسترسی هم‌زمان به لیست


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

    # اصلاح ساختار URL
    # مطمئن شویم که mirror با / تمام نشده و path با / شروع شده
    clean_mirror = mirror.rstrip('/')
    clean_path = path.lstrip('/') if path.startswith('/') else path
    
    # اگر path با v2 شروع نشد، ممکن است مشکل از سمت Docker باشد، اما معمولا می‌فرستد
    target_url = f"{clean_mirror}/{clean_path}"
    
    # اضافه کردن کوئری استرینگ اگر وجود دارد
    if request.url.query:
        target_url += f"?{request.url.query}"

    # کپی هدرها
    headers = dict(request.headers)
    
    # *** اصلاح مهم: تنظیم هدر Host به آدرس میرور ***
    # هدر Host باید دامنه میرور باشد، نه دامنه اصلی داکر
    # استخراج دامنه از URL میرور (مثلا https://mirror.com -> mirror.com)
    from urllib.parse import urlparse
    parsed_mirror = urlparse(mirror)
    host_header = parsed_mirror.hostname
    if parsed_mirror.port:
        host_header += f":{parsed_mirror.port}"
        
    headers["host"] = host_header
    
    # حذف هدرهایی که ممکن است باعث مشکل شوند
    # هدر connection را حذف می‌کنیم تا httpx خودش مدیریت کند
    headers.pop("connection", None)
    # هدر transfer-encoding را اگر هست حذف می‌کنیم تا httpx خودش محاسبه کند
    headers.pop("transfer-encoding", None)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            body = await request.body()
            
            req = client.build_request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body if body else None,
            )
            
            # ارسال درخواست
            resp = await client.send(req, stream=True)

            # بازگرداندن پاسخ
            # برخی هدرها مثل content-length یا transfer-encoding را می‌توان حذف کرد
            # یا نگه داشت. معمولاً کپی کردن همه هدرها مشکلی ندارد مگر اینکه تداخل ایجاد کند.
            resp_headers = dict(resp.headers)
            # حذف هدرهایی که نباید به کلاینت نهایی برسند
            resp_headers.pop("transfer-encoding", None)
            resp_headers.pop("connection", None)

            return StreamingResponse(
                content=resp.aiter_bytes(),
                status_code=resp.status_code,
                headers=resp_headers,
            )
    except Exception as e:
        print(f"Proxy Error for {path}: {e}")
        return Response(
            content=f"Proxy error: {str(e)}",
            status_code=502,
            media_type="text/plain",
        )
