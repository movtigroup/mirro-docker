import random
import asyncio
from typing import List, Optional, Tuple
from urllib.parse import urlparse
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx

from proxy_config import MIRRORS, HEALTH_CHECK_INTERVAL, HEALTH_CHECK_PATH

app = FastAPI(title="Docker Mirror Proxy")

healthy_mirrors_list: List[str] = []
health_lock = asyncio.Lock()

# تنظیمات کلاینت httpx به صورت global برای استفاده مجدد
# توجه: در یک اپلیکیشن بزرگتر، این مدیریت منابع باید بهینه‌تر باشد.
client_pool = {}

async def get_client():
    """
    یک کلاینت httpx برای دسترسی به mirror ها برمی‌گرداند.
    """
    mirror_url = await get_healthy_mirror()
    if not mirror_url:
        return None, None

    # اطمینان از اینکه برای هر mirror یک client داریم (یا آن را ایجاد می کنیم)
    if mirror_url not in client_pool:
        try:
            # تنظیمات کلاینت: timeout های بلندتر، verify=False برای سازگاری با برخی Mirror ها
            # max_keepalive_connections و keepalive_expiry را تنظیم می کنیم تا اتصالات پایدارتر باشند
            limits = httpx.Limits(max_connections=20, max_keepalive_connections=5) # کمی بیشتر شد
            client_pool[mirror_url] = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, read=120.0),
                limits=limits,
                verify=False # برای سازگاری با بعضی mirrors که گواهی SSL معتبر ندارند
            )
        except Exception as e:
            print(f"[CLIENT_ERROR] Error creating client for {mirror_url}: {e}")
            # اگر کلاینت ایجاد نشد، آن mirror را غیرفعال می کنیم
            await remove_unhealthy_mirror(mirror_url)
            return None, None
    
    return client_pool[mirror_url], mirror_url

async def close_clients():
    """
    همه کلاینت های httpx را می بندد.
    """
    for client in client_pool.values():
        await client.aclose()
    client_pool.clear()

async def check_mirror_health(mirror: str, client: httpx.AsyncClient) -> bool:
    """
    سلامت یک mirror را بررسی می کند.
    """
    try:
        url = f"{mirror.rstrip('/')}/{HEALTH_CHECK_PATH.lstrip('/')}"
        response = await client.get(url, timeout=5.0)
        return response.is_success
    except Exception as e:
        # print(f"[HEALTH_CHECK_FAIL] {mirror}: {e}") # برای دیباگ کردن خطاهای سلامت
        return False

async def remove_unhealthy_mirror(mirror: str):
    """
    یک mirror را از لیست healthy_mirrors حذف می کند.
    """
    async with health_lock:
        if mirror in healthy_mirrors_list:
            healthy_mirrors_list.remove(mirror)
            # همچنین کلاینت مربوط به آن را ببندید
            if mirror in client_pool:
                await client_pool[mirror].aclose()
                del client_pool[mirror]
            print(f"Mirror {mirror} removed due to unhealthiness.")


async def periodic_health_check():
    """
    به صورت دوره ای سلامت mirror ها را چک می کند.
    """
    if not MIRRORS:
        print("[WARN] No mirrors configured in proxy_config.py.")
        return

    # استفاده از کلاینت مجزا برای چک کردن سلامت
    async with httpx.AsyncClient(timeout=10.0, verify=False) as health_client:
        while True:
            print(f"Checking health of {len(MIRRORS)} mirrors...")
            tasks = [check_mirror_health(mirror, health_client) for mirror in MIRRORS]
            results = await asyncio.gather(*tasks)

            async with health_lock:
                current_healthy = []
                for mirror, is_healthy in zip(MIRRORS, results):
                    if is_healthy:
                        current_healthy.append(mirror)
                    else:
                        # اگر mirror ای قبلا سالم بوده ولی الان خراب شده، آن را حذف کن
                        if mirror in healthy_mirrors_list:
                            print(f"Mirror {mirror} is now unhealthy, removing.")
                            if mirror in client_pool:
                                await client_pool[mirror].aclose()
                                del client_pool[mirror]
                
                # جایگزینی کامل لیست healthy_mirrors
                healthy_mirrors_list[:] = current_healthy

            print(f"Healthy mirrors: {healthy_mirrors_list}")
            
            # اگر هیچ mirror ای سالم نباشد، برنامه متوقف نمی شود اما خطا می دهد
            if not healthy_mirrors_list and MIRRORS:
                print("[ERROR] All mirrors are unhealthy. Proxy will be unavailable.")

            await asyncio.sleep(HEALTH_CHECK_INTERVAL)


@app.on_event("startup")
async def startup():
    """
    هنگام شروع برنامه، سلامت اولیه mirror ها را چک می کند و تسک سلامت را اجرا می کند.
    """
    if not MIRRORS:
        print("[WARN] No mirrors configured in proxy_config.py. Proxy will not function.")
        return
        
    print("Starting health check...")
    asyncio.create_task(periodic_health_check())


@app.on_event("shutdown")
async def shutdown():
    """
    هنگام بسته شدن برنامه، همه اتصالات client را می بندد.
    """
    print("Shutting down proxy, closing clients...")
    await close_clients()


async def get_healthy_mirror() -> Optional[str]:
    """
    یک mirror سالم را به صورت تصادفی انتخاب و برمی گرداند.
    """
    async with health_lock:
        if not healthy_mirrors_list:
            return None
        return random.choice(healthy_mirrors_list)


def parse_range_header(range_header: str) -> Optional[Tuple[int, Optional[int]]]:
    """
    هدر Range را تجزیه می کند و یک tuple از start و end برمی گرداند.
    """
    if not range_header or not range_header.startswith("bytes="):
        return None
    parts = range_header[6:].split("-")
    if len(parts) != 2:
        return None
    try:
        start = int(parts[0])
        end_str = parts[1]
        end = int(end_str) if end_str else None
        return start, end
    except ValueError:
        return None


@app.api_route("/{path:path}", methods=["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    """
    درخواست ها را به یکی از mirror های سالم پرواکسی می کند.
    """
    client, mirror = await get_client()
    if client is None or mirror is None:
        return Response(content="No healthy mirror available", status_code=503, media_type="text/plain")

    # فقط درخواست های مربوط به Docker Registry API (v2) را پرواکسی می کنیم
    if not path.startswith("v2/"):
        return Response(content="Docker Registry API must start with /v2/", status_code=404, media_type="text/plain")

    # ساخت URL مقصد
    clean_mirror = mirror.rstrip('/')
    clean_path = path if path.startswith('/') else f"/{path}"
    target_url = f"{clean_mirror}{clean_path}" # /v2/ را خودش دارد
    if request.url.query:
        target_url += f"?{request.url.query}"

    # آماده سازی هدرها برای ارسال به upstream
    headers = dict(request.headers)
    
    # اصلاح هدر Host
    parsed_mirror = urlparse(mirror)
    host_header = parsed_mirror.hostname
    if parsed_mirror.port:
        host_header += f":{parsed_mirror.port}"
    headers["host"] = host_header

    # حذف هدرهای غیر ضروری یا تداخلی
    headers.pop("connection", None)
    headers.pop("transfer-encoding", None) # httpx این را به درستی مدیریت می کند
    headers.pop("accept-encoding", None)    # برای اینکه mirror همیشه content اصلی را بدهد
    
    # حذف هدرهای X- (معمولا برای متادیتا یا هدایت به خود proxy هستند)
    for header_name in list(headers.keys()):
        if header_name.lower().startswith("x-"):
            del headers[header_name]

    # مدیریت هدر Range
    range_header = headers.pop("range", None)
    parsed_range = parse_range_header(range_header) if range_header else None
    original_range_header = range_header # برای نمایش در لاگ

    print(f"[*] Proxying: {request.method} {target_url}" +
          (f" (Range: {original_range_header})" if original_range_header else ""))

    try:
        # خواندن بدنه درخواست (در صورت وجود)
        # برای درخواست های GET و HEAD که بدنه ندارند، body خالی خواهد بود
        body = await request.body()

        # ارسال هدر Range به upstream mirror در صورت وجود
        if original_range_header:
            headers["range"] = original_range_header

        # ساخت و ارسال درخواست به mirror
        req = client.build_request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body if body else None,
        )
        resp = await client.send(req, stream=True)

        # اگر upstream خطایی برگرداند (status code >= 400)
        if resp.status_code >= 400:
            error_body = await resp.aread()
            print(f"[ERROR] Mirror {mirror} returned {resp.status_code}: {error_body.decode('utf-8', errors='ignore')}")
            # پاسخ خطا را مستقیماً برگردان
            return Response(content=error_body, status_code=resp.status_code, headers=dict(resp.headers))

        # --- پردازش پاسخ از Mirror ---

        # حالت 1: Mirror خودش 206 Partial Content برگرداند (همه چیز درست است)
        if resp.status_code == 206:
            resp_headers = dict(resp.headers)
            resp_headers.pop("transfer-encoding", None) # حذف هدر غیرضروری
            resp_headers.pop("connection", None) # حذف هدر غیرضروری

            async def stream_206_from_mirror():
                try:
                    async for chunk in resp.aiter_bytes():
                        yield chunk
                except httpx.ReadError as e:
                    print(f"[STREAM_READ_ERROR_206] {mirror} {target_url}: {e}")
                except Exception as e:
                    print(f"[STREAM_ERROR_206] {mirror} {target_url}: {e}")
                finally:
                    await resp.aclose() # اطمینان از بسته شدن پاسخ

            return StreamingResponse(content=stream_206_from_mirror(), status_code=206, headers=resp_headers)

        # حالت 2: Mirror پاسخ 200 OK داد، اما ما Range خواسته بودیم
        # در این حالت، ما باید خودمان پاسخ 206 را بسازیم
        if parsed_range and resp.status_code == 200:
            
            # سعی می کنیم Content-Length را بگیریم
            content_length_header = resp.headers.get("content-length")
            
            # اگر Content-Length اصلی را نتوانیم بگیریم، مجبوریم کل chunk ها را بخوانیم
            # این برای فایل های بزرگ ممکن است حافظه زیادی مصرف کند
            if content_length_header is None:
                print(f"[WARN] {mirror} {target_url}: No Content-Length in 200 OK response. Reading all data to satisfy Range.")
                # تمام داده ها را در حافظه می خوانیم
                full_content = await resp.aread()
                total_length = len(full_content)
            else:
                total_length = int(content_length_header)

            start_byte = parsed_range[0]
            end_byte_requested = parsed_range[1]
            
            # محاسبه end byte واقعی
            # اگر end_byte_requested null باشد، تا انتهای فایل را می خواهیم
            # اما همیشه باید از total_length کمتر باشد
            end_byte = min(end_byte_requested if end_byte_requested is not None else total_length - 1, total_length - 1)

            # بررسی اعتبار Range
            if start_byte >= total_length:
                # Range not satisfiable
                await resp.aclose() # بستن پاسخ upstream
                return Response(content="Range not satisfiable", status_code=416, media_type="text/plain")
            
            # محاسبه طول داده ای که باید برگردانده شود
            final_content_length = end_byte - start_byte + 1

            # ساخت هدرهای پاسخ 206
            resp_headers = dict(resp.headers)
            resp_headers.pop("transfer-encoding", None)
            resp_headers.pop("connection", None)
            resp_headers["content-range"] = f"bytes {start_byte}-{end_byte}/{total_length}"
            resp_headers["content-length"] = str(final_content_length)
            resp_headers.pop("status", None) # حذف هدر status که گاهی httpx اضافه می کند

            # اگر محتوا کامل خوانده شده بود (حالت content_length_header is None)
            if content_length_header is None:
                partial_content = full_content[start_byte : start_byte + final_content_length]
                await resp.aclose() # اطمینان از بسته شدن پاسخ
                return Response(
                    content=partial_content,
                    status_code=206,
                    headers=resp_headers,
                    media_type=resp.headers.get("content-type", "application/octet-stream")
                )
            else:
                # اگر Content-Length وجود داشت، محتوا را به صورت استریم برش می دهیم
                async def stream_range_from_200():
                    bytes_sent_so_far = 0
                    try:
                        async for chunk in resp.aiter_bytes():
                            # محاسبه قسمتی از chunk که به Range ما تعلق دارد
                            # start_byte_in_chunk: شروع داده قابل استفاده در این chunk
                            # end_byte_in_chunk: انتهای داده قابل استفاده در این chunk
                            start_byte_in_chunk = max(0, start_byte - bytes_sent_so_far)
                            end_byte_in_chunk = min(len(chunk), start_byte + final_content_length - bytes_sent_so_far)
                            
                            data_to_yield = chunk[start_byte_in_chunk:end_byte_in_chunk]

                            if data_to_yield:
                                yield data_to_yield
                                bytes_sent_so_far += len(data_to_yield)

                            if bytes_sent_so_far >= final_content_length:
                                break
                    except httpx.ReadError as e:
                        print(f"[RANGE_STREAM_ERROR_200] {mirror} {target_url}: {e}")
                    except Exception as e:
                        print(f"[RANGE_STREAM_ERROR_200] {mirror} {target_url}: {e}")
                    finally:
                        await resp.aclose() # اطمینان از بسته شدن پاسخ

                return StreamingResponse(
                    content=stream_range_from_200(),
                    status_code=206,
                    headers=resp_headers,
                    media_type=resp.headers.get("content-type", "application/octet-stream")
                )

        # حالت 3: درخواست عادی (بدون Range) یا response از mirror بدون Content-Length
        # در این حالت، داده ها را بدون تغییر برمی گردانیم
        resp_headers = dict(resp.headers)
        resp_headers.pop("transfer-encoding", None) # حذف هدر غیرضروری
        resp_headers.pop("connection", None) # حذف هدر غیرضروری

        async def stream_normal_response():
            try:
                async for chunk in resp.aiter_bytes():
                    yield chunk
            except httpx.ReadError as e:
                print(f"[STREAM_READ_ERROR_NORMAL] {mirror} {target_url}: {e}")
            except Exception as e:
                print(f"[STREAM_ERROR_NORMAL] {mirror} {target_url}: {e}")
            finally:
                await resp.aclose() # اطمینان از بسته شدن پاسخ

        return StreamingResponse(
            content=stream_normal_response(),
            status_code=resp.status_code,
            headers=resp_headers,
        )

    except httpx.ReadTimeout as e:
        print(f"[TIMEOUT] {mirror} {target_url}: {e}")
        await remove_unhealthy_mirror(mirror) # این mirror timeout داده، پس غیرفعالش کن
        return Response(content="Upstream mirror timed out", status_code=504, media_type="text/plain")
    except httpx.ConnectTimeout as e:
        print(f"[CONNECT_TIMEOUT] {mirror} {target_url}: {e}")
        await remove_unhealthy_mirror(mirror) # اتصال ناموفق بوده
        return Response(content="Upstream mirror connection timed out", status_code=504, media_type="text/plain")
    except httpx.RequestError as e:
        print(f"[REQUEST_ERROR] {mirror} {target_url}: {e}")
        await remove_unhealthy_mirror(mirror) # خطای درخواست عمومی
        return Response(content=f"Error communicating with upstream mirror: {e}", status_code=502, media_type="text/plain")
    except RuntimeError as e:
        # این خطا معمولا مربوط به بسته شدن غیرمنتظره کانکشن یا مشکلات Stream است
        print(f"[RUNTIME_ERROR] {mirror} {target_url}: {e}")
        await remove_unhealthy_mirror(mirror) # این نوع خطاها معمولا نشان دهنده ناپایداری mirror هستند
        return Response(content=f"Proxy stream error: {e}", status_code=502, media_type="text/plain")
    except Exception as e:
        print(f"[UNKNOWN_PROXY_ERROR] {mirror} {target_url}: {e}")
        await remove_unhealthy_mirror(mirror) # هر خطای ناشناخته دیگری
        return Response(content=f"An unexpected proxy error occurred: {str(e)}", status_code=502, media_type="text/plain")
