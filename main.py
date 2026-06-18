import random
import asyncio
import httpx
from typing import List, Optional, Tuple
from urllib.parse import urlparse
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

from proxy_config import (
    MIRRORS, HEALTH_CHECK_INTERVAL, HEALTH_CHECK_PATH,
    TIER1_MIRRORS, IRANIAN_MIRRORS, TIER2_MIRRORS, PACKAGE_MIRRORS
)

app = FastAPI(title="Docker Mirror Proxy")

healthy_mirrors_list: List[str] = []
health_lock = asyncio.Lock()

# Global client pool for reuse
client_pool = {}

async def get_proxy_client(mirror_url: str):
    """Returns an httpx client for a specific mirror."""
    if mirror_url not in client_pool:
        try:
            limits = httpx.Limits(max_connections=50, max_keepalive_connections=10)
            client_pool[mirror_url] = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, read=120.0),
                limits=limits,
                verify=False
            )
        except Exception as e:
            print(f"[CLIENT_ERROR] Error creating client for {mirror_url}: {e}")
            return None
    return client_pool[mirror_url]

async def check_mirror_health(mirror: str, client: httpx.AsyncClient) -> bool:
    """Checks health of a single mirror."""
    try:
        url = f"{mirror.rstrip('/')}/{HEALTH_CHECK_PATH.lstrip('/')}"
        response = await client.get(url, timeout=5.0)
        return response.is_success
    except Exception:
        return False

async def remove_unhealthy_mirror(mirror: str):
    """Removes a mirror from the healthy list."""
    async with health_lock:
        if mirror in healthy_mirrors_list:
            healthy_mirrors_list.remove(mirror)
            if mirror in client_pool:
                await client_pool[mirror].aclose()
                del client_pool[mirror]
            print(f"Mirror {mirror} removed due to unhealthiness.")

async def periodic_health_check():
    """Periodically checks mirror health."""
    async with httpx.AsyncClient(timeout=10.0, verify=False) as health_client:
        while True:
            tasks = [check_mirror_health(mirror, health_client) for mirror in MIRRORS]
            results = await asyncio.gather(*tasks)

            async with health_lock:
                current_healthy = [mirror for mirror, healthy in zip(MIRRORS, results) if healthy]
                healthy_mirrors_list.clear()
                healthy_mirrors_list.extend(current_healthy)
                print(f"Health check complete. {len(healthy_mirrors_list)} mirrors are healthy.")
            
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(periodic_health_check())

@app.on_event("shutdown")
async def shutdown_event():
    for client in client_pool.values():
        await client.aclose()
    client_pool.clear()

async def get_healthy_mirror(is_package: bool = False) -> Optional[str]:
    """Selects a healthy mirror based on tiered priority."""
    if is_package:
        # For packages, we don't have health checks yet, so we pick one randomly
        return random.choice(PACKAGE_MIRRORS)

    async with health_lock:
        if not healthy_mirrors_list:
            return None

        # Priority: Tier 1 -> Iranian -> Tier 2
        for tier in [TIER1_MIRRORS, IRANIAN_MIRRORS, TIER2_MIRRORS]:
            healthy_in_tier = [m for m in tier if m in healthy_mirrors_list]
            if healthy_in_tier:
                return random.choice(healthy_in_tier)

        return random.choice(healthy_mirrors_list)

def parse_range_header(range_header: str) -> Optional[Tuple[int, Optional[int]]]:
    if not range_header or not range_header.startswith("bytes="):
        return None
    try:
        parts = range_header.replace("bytes=", "").split("-")
        start = int(parts[0])
        end = int(parts[1]) if parts[1] else None
        return start, end
    except (ValueError, IndexError):
        return None

@app.api_route("/{path:path}", methods=["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    # Detect GPG or Package requests
    is_package = any(x in path.lower() for x in ["gpg", "linux/ubuntu", "linux/debian", "linux/centos", "linux/static", "linux/fedora"])

    mirror = await get_healthy_mirror(is_package=is_package)
    if not mirror:
        return Response(content="No healthy mirror available", status_code=503, media_type="text/plain")

    client = await get_proxy_client(mirror)
    if not client:
        return Response(content="Proxy client error", status_code=500)

    target_url = f"{mirror.rstrip('/')}/{path}"
    headers = dict(request.headers)
    
    parsed_mirror = urlparse(mirror)
    host_header = parsed_mirror.hostname
    if parsed_mirror.port:
        host_header += f":{parsed_mirror.port}"
    headers["host"] = host_header

    for h in ["connection", "transfer-encoding", "accept-encoding"]:
        headers.pop(h, None)
    for h in list(headers.keys()):
        if h.lower().startswith("x-"):
            del headers[h]

    range_header = headers.get("range")
    parsed_range = parse_range_header(range_header) if range_header else None

    try:
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
            return Response(content=error_body, status_code=resp.status_code, headers=dict(resp.headers))

        # Handle Range Requests (206)
        if parsed_range and resp.status_code == 200:
            content_length = resp.headers.get("content-length")
            if not content_length:
                full_content = await resp.aread()
                total_length = len(full_content)
            else:
                total_length = int(content_length)

            start_byte, end_byte_req = parsed_range
            end_byte = min(end_byte_req if end_byte_req is not None else total_length - 1, total_length - 1)

            if start_byte >= total_length:
                await resp.aclose()
                return Response(content="Range not satisfiable", status_code=416)

            final_len = end_byte - start_byte + 1
            resp_headers = dict(resp.headers)
            resp_headers.update({
                "content-range": f"bytes {start_byte}-{end_byte}/{total_length}",
                "content-length": str(final_len)
            })
            resp_headers.pop("transfer-encoding", None)

            async def stream_range():
                sent = 0
                async for chunk in resp.aiter_bytes():
                    s_in_c = max(0, start_byte - sent)
                    e_in_c = min(len(chunk), start_byte + final_len - sent)
                    data = chunk[s_in_c:e_in_c]
                    if data:
                        yield data
                        sent += len(data)
                    if sent >= final_len: break
                await resp.aclose()

            return StreamingResponse(stream_range(), status_code=206, headers=resp_headers)

        # Normal response
        resp_headers = dict(resp.headers)
        resp_headers.pop("transfer-encoding", None)

        async def stream_resp():
            async for chunk in resp.aiter_bytes():
                yield chunk
            await resp.aclose()

        return StreamingResponse(stream_resp(), status_code=resp.status_code, headers=resp_headers)

    except Exception as e:
        print(f"[PROXY_ERROR] {e}")
        await remove_unhealthy_mirror(mirror)
        return Response(content=f"Proxy error: {str(e)}", status_code=502)
