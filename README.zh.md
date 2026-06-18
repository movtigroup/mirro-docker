<div align="center">

# 🐳 Docker 智能镜像代理

**专为受限网络和优化连接设计的 Docker 智能镜像代理**

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green?logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)

</div>

---

## 📋 简介

本项目是一个基于 **FastAPI** 构建的 **Docker 智能镜像代理**。它能够根据健康检查和优先级分层（首选本地/高速镜像）自动处理镜像选择。

### 核心特性：
- **分层选择：** 根据可用性在 Tier 1、伊朗镜像和 Tier 2（全球/中国镜像）之间自动切换。
- **GPG 与 软件包支持：** 支持代理 Docker GPG 密钥和安装包（apt/yum）请求，重定向至高速镜像（清华、阿里、Hetzner、OVH 等）。
- **健康检查：** 定期验证上游镜像状态，确保服务零停机。
- **流式响应：** 高效流式传输大型 Docker 分层，无高内存占用。

---

## 🚀 快速开始

### 选项 1：使用公开镜像（推荐）

编辑 Docker 守护程序配置（例如：/etc/docker/daemon.json）：

```json
{
  "registry-mirrors": ["https://docker.ththt.ir"],
  "insecure-registries": ["https://docker.ththt.ir"]
}
```

重启 Docker：

```bash
sudo systemctl restart docker
```

---

### 选项 2：自行托管

#### 1. 环境要求
确保已安装 Docker 和 Docker Compose。

#### 2. 克隆并运行

```bash
git clone https://github.com/movtigroup/mirro-docker.git
cd mirro-docker
docker-compose up -d --build
```

#### 3. 自定义配置

编辑 `proxy_config.py` 来自定义您的镜像分层：

```python
TIER1_MIRRORS = [...]
IRANIAN_MIRRORS = [...]
TIER2_MIRRORS = [...]
PACKAGE_MIRRORS = [...]
```

---

## ⚙️ 工作原理

- **健康检查：** 默认每 60 秒通过 `GET /v2/` 进行一次检查。
- **故障转移逻辑：** 优先级顺序为 Tier 1 -> 伊朗镜像 -> Tier 2。如果当前层级的所有镜像都失效，将自动回退到下一层。
- **软件包代理：** 自动检测安装请求（如 `linux/ubuntu`, `gpg`）并将其路由至专用的高速软件包镜像。

---

## 📄 许可证

本项目基于 **MIT 许可证** 发布。

---

<div align="center">

**✨ 如果觉得有用，请给我们一个 ⭐️！**

</div>
