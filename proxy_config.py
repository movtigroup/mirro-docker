import ipaddress
from urllib.parse import urlparse

# --- Docker mirrors: ایران (اولویت اول برای /v2/*) ---
DOCKER_IRANIAN_MIRRORS = [
    "https://docker.iranserver.com",
    "https://docker.abrha.net",
    "https://docker.arvancloud.ir",
    "https://mirror2.chabokan.net",
    "https://docker.derak.cloud",
    "https://docker.devneeds.ir",
    "https://docker.hyperclouds.ir",
]

# --- Docker mirrors: خارجی ---
DOCKER_FOREIGN_MIRRORS = [
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

# --- Linux repository mirrors (برای مسیرهای غیر /v2/*) ---
LINUX_REPO_MIRRORS = [
    "https://miravaorg.ir/",
    "https://mirror.rasanegaar.com/",
    "https://github.com/MiravaOrg/Mirava",
    "https://mirror.kargadan.ir/parch",
    "https://linuxmirrors.ir/",
    "https://parchlinux.com/en/repo",
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


def _normalize(url: str) -> str:
    return url.strip().rstrip("/")


IRANIAN_MIRRORS = [_normalize(u) for u in DOCKER_IRANIAN_MIRRORS if _is_valid_mirror(u)]
FOREIGN_MIRRORS = [_normalize(u) for u in DOCKER_FOREIGN_MIRRORS if _is_valid_mirror(u)]
DOCKER_MIRRORS = list(dict.fromkeys(IRANIAN_MIRRORS + FOREIGN_MIRRORS))
REPO_MIRRORS = [_normalize(u) for u in LINUX_REPO_MIRRORS if _is_valid_mirror(u)]

MIRRORS = list(dict.fromkeys(DOCKER_MIRRORS + REPO_MIRRORS))

# مسیر Health Check هر میرور (Docker ها با /v2/، سایر ریپوها با /)
MIRROR_HEALTH_PATHS = {mirror: "/" for mirror in MIRRORS}
MIRROR_HEALTH_PATHS.update({mirror: "/v2/" for mirror in DOCKER_MIRRORS})

HEALTH_CHECK_INTERVAL = 60
