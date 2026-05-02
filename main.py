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

    # *** اصلاح مهم: اطمینان از اینکه مسیر با /v2/ شروع می‌شود ***
    # Docker Registry API همیشه با /v2/ شروع می‌شود.
    # اگر درخواستی به / یا /favicon.ico آمد، آن را رد می‌کنیم یا به /v2/ هدایت می‌کنیم.
    # اما برای سادگی، فرض می‌کنیم درخواست‌های Docker همیشه /v2/ دارند.
    # اگر path با /v2/ شروع نشد، احتمالاً درخواست مرورگر است (مثل favicon).
    
    if not path.startswith("v2/"):
        # اگر درخواست برای /v2/ نیست، می‌توانیم یک خطای مناسب برگردانیم
        # یا آن را به /v2/ هدایت کنیم. اینجا برای سادگی خطای 404 می‌دهیم.
        return Response(
            content="Docker Registry API must start with /v2/",
            status_code=404,
            media_type="text/plain",
        )

    # ساختن URL هدف
    clean_mirror = mirror.rstrip('/')
    # مطمئن شویم path با / شروع می‌شود
    clean_path = path if path.startswith('/') else f"/{path}"
    target_url = f"{clean_mirror}{clean_path}"
    
    # اضافه کردن کوئری استرینگ اگر وجود دارد
    if request.url.query:
        target_url += f"?{request.url.query}"

    # کپی هدرها
    headers = dict(request.headers)
    
    # *** تنظیم هدر Host به آدرس میرور ***
    parsed_mirror = urlparse(mirror)
    host_header = parsed_mirror.hostname
    if parsed_mirror.port:
        host_header += f":{parsed_mirror.port}"
        
    headers["host"] = host_header
    
    # حذف هدرهایی که ممکن است باعث مشکل شوند
    headers.pop("connection", None)
    headers.pop("transfer-encoding", None)
    # هدر accept را نگه می‌داریم چون Docker برای تشخیص نوع محتوا به آن نیاز دارد

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

            # اگر پاسخ خطا بود (مثل 400)، آن را مستقیماً برگردانیم
            if resp.status_code >= 400:
                # خواندن بدنه خطا برای دیباگ
                error_body = await resp.aread()
                return Response(
                    content=error_body.decode('utf-8', errors='ignore'),
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                )

            # بازگرداندن پاسخ به صورت stream
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
