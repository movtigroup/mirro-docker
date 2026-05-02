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
    """
    یک میرور را با فرستادن درخواست GET به HEALTH_CHECK_PATH بررسی می‌کند.
    اگر status 200 برگرداند، سالم در نظر گرفته می‌شود.
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

            # (اختیاری) لاگ وضعیت
            print(f"Healthy mirrors: {healthy_mirrors}")

            await asyncio.sleep(HEALTH_CHECK_INTERVAL)


@app.on_event("startup")
async def startup():
    """شروع Health Check در background بعد از بالا آمدن اپ"""
    asyncio.create_task(periodic_health_check())


def get_healthy_mirror() -> Optional[str]:
    """یک میرور سالم به صورت تصادفی برمی‌گرداند"""
    async with health_lock:
        if not healthy_mirrors:
            return None
        return random.choice(healthy_mirrors)


@app.api_route("/{path:path}", methods=["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    """
    تمام درخواست‌ها را دریافت کرده و به یک میرور سالم پراکسی می‌کند.
    از stream برای بدنه پاسخ استفاده می‌شود تا فایل‌های حجیم (مثل لایه‌های داکر) 
    بدون بارگذاری کامل در حافظه عبور کنند.
    """
    mirror = get_healthy_mirror()
    if mirror is None:
        return Response(
            content="No healthy mirror available",
            status_code=503,
            media_type="text/plain",
        )

    # ساختن URL هدف
    target_url = f"{mirror.rstrip('/')}/{path.lstrip('/')}"
    query = request.url.query
    if query:
        target_url += f"?{query}"

    # آماده‌سازی هدرها (بعضی هدرها مثل host باید تنظیم شود)
    headers = dict(request.headers)
    headers.pop("host", None)  # هاست اصلی حذف شود

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # ارسال درخواست به mirror
            req = client.build_request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=await request.body(),
            )
            resp = await client.send(req, stream=True)

            # بازگرداندن پاسخ به صورت stream
            return StreamingResponse(
                content=resp.aiter_bytes(),
                status_code=resp.status_code,
                headers=dict(resp.headers),
            )
    except Exception as e:
        return Response(
            content=f"Proxy error: {str(e)}",
            status_code=502,
            media_type="text/plain",
        )
