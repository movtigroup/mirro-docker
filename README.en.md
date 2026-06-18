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

#### 1. Setup Docker Registry
Edit your Docker Daemon configuration (e.g., `/etc/docker/daemon.json`):

```json
{
  "registry-mirrors": ["https://docker.ththt.ir"],
  "insecure-registries": ["https://docker.ththt.ir"]
}
```

Restart Docker: `sudo systemctl restart docker`.

#### 2. Usage for GPG and Repositories (Docker Install)
You can also use this proxy to fetch GPG keys and install Docker:

```bash
# Fetch GPG key
curl -fsSL https://docker.ththt.ir/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add apt repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://docker.ththt.ir/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
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

---

## ⚙️ How it Works

- **Health Check:** Runs every 60 seconds (default).
- **Failover Logic:** Priority order is Tier 1 -> Iranian -> Tier 2.
- **Package Proxying:** Automatically detects installation requests and routes them to dedicated high-speed package mirrors.

---

## 📄 License

This project is released under the **MIT License**.

---

<div align="center">

**✨ Support us by giving a ⭐️ to this repository!**

</div>
