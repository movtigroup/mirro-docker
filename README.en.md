<div align="center">

# 🐳 Docker Mirror Proxy

**Smart Docker Mirror Proxy for restricted networks and optimized connectivity**

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green?logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)

</div>

---

## 📋 Introduction

This repository contains a **Smart Docker Mirror Proxy** built with **FastAPI**. It automatically handles mirror selection based on health checks and prioritized tiers (local/fastest mirrors first).

### Key Features:
- **Tiered Selection:** Automatically switches between Tier 1, Iranian, and Tier 2 (Global) mirrors based on availability.
- **GPG & Package Support:** Proxies requests for Docker GPG keys and installation packages (apt/yum) to high-speed mirrors (Tsinghua, Aliyun, Hetzner, OVH, etc.).
- **Health Checks:** Periodically verifies upstream mirror health to ensure zero downtime.
- **Streaming Response:** Efficiently streams large Docker layers without high memory overhead.

---

## 🚀 Quick Start

### Option 1: Using the Public Mirror (Recommended)

Edit your Docker Daemon configuration (e.g., /etc/docker/daemon.json):

```json
{
  "registry-mirrors": ["https://docker.ththt.ir"],
  "insecure-registries": ["https://docker.ththt.ir"]
}
```

Restart Docker:

```bash
sudo systemctl restart docker
```

---

### Option 2: Self-Hosting

#### 1. Requirements
Ensure Docker and Docker Compose are installed.

#### 2. Clone and Run

```bash
git clone https://github.com/movtigroup/mirro-docker.git
cd mirro-docker
docker-compose up -d --build
```

#### 3. Configuration

Edit `proxy_config.py` to customize your tiers:

```python
TIER1_MIRRORS = [...]
IRANIAN_MIRRORS = [...]
TIER2_MIRRORS = [...]
PACKAGE_MIRRORS = [...]
```

---

## ⚙️ How it Works

- **Health Check:** Runs every 60 seconds (default) via `GET /v2/`.
- **Failover Logic:** Priority order is Tier 1 -> Iranian -> Tier 2. If all mirrors in a tier fail, it falls back to the next one.
- **Package Proxying:** Automatically detects installation requests (e.g., `linux/ubuntu`, `gpg`) and routes them to dedicated high-speed package mirrors.

---

## 📄 License

This project is released under the **MIT License**.

---

<div align="center">

**✨ Support us by giving a ⭐️ to this repository!**

</div>
