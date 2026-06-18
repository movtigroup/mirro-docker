# Tier 1 Mirrors (High Priority)
TIER1_MIRRORS = [
    "https://repo.abrha.net/docker",
    "https://docker.iranserver.com",
]

# Iranian Mirrors
IRANIAN_MIRRORS = [
    "https://docker.arvancloud.ir",
    "https://mirror2.chabokan.net",
    "https://docker.derak.cloud",
]

# Tier 2 / International Registry Mirrors
TIER2_MIRRORS = [
    "https://docker.1ms.run",
    "https://dockerproxy.net",
    "https://docker.m.daocloud.io",
    "https://docker.1panel.live",
    "https://registry.cn-hangzhou.aliyuncs.com",
    "https://registry.cn-shanghai.aliyuncs.com",
    "https://registry.cn-qingdao.aliyuncs.com",
    "https://registry.cn-beijing.aliyuncs.com",
    "https://registry.cn-zhangjiakou.aliyuncs.com",
    "https://registry.cn-huhehaote.aliyuncs.com",
    "https://registry.cn-wulanchabu.aliyuncs.com",
    "https://registry.cn-shenzhen.aliyuncs.com",
    "https://registry.cn-heyuan.aliyuncs.com",
    "https://registry.cn-guangzhou.aliyuncs.com",
    "https://registry.cn-chengdu.aliyuncs.com",
    "https://registry.cn-hongkong.aliyuncs.com",
    "https://registry.ap-northeast-1.aliyuncs.com",
    "https://registry.ap-southeast-1.aliyuncs.com",
    "https://registry.ap-southeast-3.aliyuncs.com",
    "https://registry.ap-southeast-5.aliyuncs.com",
    "https://registry.eu-central-1.aliyuncs.com",
    "https://registry.eu-west-1.aliyuncs.com",
    "https://registry.us-west-1.aliyuncs.com",
    "https://registry.us-east-1.aliyuncs.com",
    "https://registry.me-east-1.aliyuncs.com",
    "https://mirror.ccs.tencentyun.com",
    "https://gcr.io",
    "https://asia.gcr.io",
    "https://eu.gcr.io",
]

# Package & GPG Mirrors (for apt/yum and gpg keys)
# These are used when the request path matches package or gpg patterns
PACKAGE_MIRRORS = [
    "https://mirrors.tuna.tsinghua.edu.cn/docker-ce",
    "https://mirrors.ustc.edu.cn/docker-ce",
    "https://mirrors.aliyun.com/docker-ce",
    "https://mirrors.huaweicloud.com/docker-ce",
    "https://mirrors.cloud.tencent.com/docker-ce",
    "https://download.docker.com",
    "https://mirror.hetzner.com/docker-ce",
    "https://vps-mirror.ovh.net/docker-ce",
]

# Combined list for health checks (Registry API)
MIRRORS = TIER1_MIRRORS + IRANIAN_MIRRORS + TIER2_MIRRORS

HEALTH_CHECK_INTERVAL = 60
HEALTH_CHECK_PATH = "/v2/"
