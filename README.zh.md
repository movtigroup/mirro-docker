<div align="center">

# 🐳 Docker 镜像代理

**专为受限环境和全球可用性设计的智能 Docker 镜像代理**

[![自动打标签和发布](https://github.com/movtigroup/mirro-docker/actions/workflows/release.yml/badge.svg)](https://github.com/movtigroup/mirro-docker/actions/workflows/release.yml)
![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green?logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)

[فارسی](README.md) | [English](README.en.md) | [简体中文](README.zh.md)

</div>

---

## 📋 简介

此存储库包含使用 **FastAPI** 构建的 **智能 Docker 镜像代理** 的源代码。它通过智能地将请求路由到健康的镜像站，帮助绕过网络限制并提供更快的 Docker 镜像访问速度。

您可以：
- **直接使用** 已托管的镜像站。
- **在您自己的服务器上部署**，使用 Docker Compose 并自定义镜像列表。

系统会自动对所有配置的镜像站进行健康检查，并将 Docker Daemon 的请求重定向到健康的候选镜像站之一。

---

## 🚀 快速开始

### 方案一：使用托管镜像站

编辑您的 Docker Daemon 配置文件（例如 `/etc/docker/daemon.json`）：

```json
{
  "registry-mirrors": ["https://your-proxy-domain.com"],
  "insecure-registries": ["https://your-proxy-domain.com"]
}
```

重启 Docker：

```bash
sudo systemctl restart docker
```

---

### 方案二：部署您自己的服务

#### 1. 前提条件

确保您的服务器上已安装 Docker 和 Docker Compose。

#### 2. 克隆并运行

```bash
git clone https://github.com/movtigroup/mirro-docker.git
cd mirro-docker
docker-compose up -d --build
```

---

## ⚙️ 工作原理

- **健康检查：** 服务定期（默认 60 秒）通过发送 `GET /v2/` 请求检查列表中的所有镜像站。
- **反向代理：** 客户端请求被路由到健康的镜像站之一（随机选择）。
- **流式传输：** 响应采用流式传输处理，以处理大型 Docker 层，而不会产生高内存消耗。
- **故障转移：** 如果所有镜像站都宕机，它将返回 503 错误。

---

## 🔧 自定义镜像站

编辑 `proxy_config.py`：

```python
MIRRORS = [
    "https://docker.m.daocloud.io",
    "https://docker.mirrors.ustc.edu.cn",
    "https://mirror.hetzner.com",
    "https://docker.ovh.net",
    # ... 添加更多
]
```

修改后重启服务：

```bash
docker-compose restart
```

---

## 🗂 项目结构

```
.
├── main.py              # FastAPI 应用程序（代理逻辑）
├── proxy_config.py      # 配置和镜像站列表
├── requirements.txt     # Python 依赖项
├── Dockerfile           # Docker 镜像定义
├── docker-compose.yml   # 服务定义
└── README.md            # 波斯语文档
```

---

## 📄 许可证

本项目采用 **MIT 许可证** 发布。

---

<div align="center">

**✨ 给这个存储库点个 ⭐️ 来支持我们！**

</div>
