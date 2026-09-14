import ipaddress
from urllib.parse import urlparse

# --- میرورهای ایرانی (اولویت اول) ---
IRANIAN_MIRRORS = [
    "https://docker.iranserver.com",
    "https://docker.abrha.net",
    "https://docker.arvancloud.ir",
    "https://mirror2.chabokan.net",
    "https://docker.derak.cloud",
    "https://docker.devneeds.ir",
    "https://docker.hyperclouds.ir",
    "https://docker-registry.rasanegaar.com",
    "https://docker.mobinhost.com",
    "https://docker.kernel.ir",
    "https://mirrors.pardisco.co",
    "https://focker.ir",
    "https://hub.megan.ir",
    "https://mirrors.pardisco.co",
    "https://hub.atlantiscloud.ir",
    "https://ghcr.atlantiscloud.ir",
    "https://quay.atlantiscloud.ir",
    "https://docker.DockerMe.ir",
    "https://registry.docker.ir",
    "https://docker-mirror.kargadan.ir",
    "https://docker-quay-mirror.kargadan.ir",
    
]

# --- میرورهای چینی ---
FOREIGN_MIRRORS = [
    "https://docker.m.daocloud.io",
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com",
    "https://ccr.ccs.tencentyun.com",
    "https://docker.nju.edu.cn",
    "https://docker.1panel.live",
    "https://registry.docker-cn.com",
    "https://hub.rat.dev",
    "https://docker.xuanyuan.me",
    "https://dockerhub.icu",
    "https://hub.uuuadc.top",
    "https://docker.awsl9527.cn",
    "https://mirrors.tuna.tsinghua.edu.cn/",
    "https://docker.1ms.run",
    

    
    # --- اروپا، آمریکا و سایر مناطق ---
    "https://dockerproxy.net",
    "https://docker.imgdb.de",
    "https://docker.1ms.run",
    "https://registry.mirror.hetzner.com",
    "https://docker.ovh.net",
    "https://mirror.gcr.io",
    "https://registry.eu-central-1.aliyuncs.com",
    "https://registry.eu-west-1.aliyuncs.com",
    "https://registry.us-west-1.aliyuncs.com",
    "https://registry.us-east-1.aliyuncs.com",
    "https://registry.me-east-1.aliyuncs.com",
    "https://registry.ap-northeast-1.aliyuncs.com",
    "https://registry.ap-southeast-1.aliyuncs.com",
    "https://gcr.io",
    "https://ghcr.io",
]


def _is_valid_mirror(url: str) -> bool:
    """
    اعتبارسنجی میرور: فقط http/https با هاست عمومی مجاز است.
    localhost، loopback و آدرس‌های IP خصوصی/رزرو رد می‌شوند.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        return False
    try:
        addr = ipaddress.ip_address(host)
        if not addr.is_global:
            return False
    except ValueError:
        # hostname یک نام دامنه است، نه IP literal
        pass
    return True


MIRRORS = [u.rstrip("/") for u in IRANIAN_MIRRORS + FOREIGN_MIRRORS if _is_valid_mirror(u)]

HEALTH_CHECK_INTERVAL = 60
HEALTH_CHECK_PATH = "/v2/"
