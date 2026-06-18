<div align="center">

# 🐳 Docker Mirror Proxy

**Smart Docker Mirror Proxy for restricted environments and global availability**

[![Publish Docker image](https://github.com/movtigroup/mirro-docker/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/movtigroup/mirro-docker/actions/workflows/docker-publish.yml)
![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green?logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)

[فارسی](README.md) | [English](README.en.md) | [简体中文](README.zh.md)

</div>

---

## 📋 Overview

This repository contains the source code for a **Smart Docker Mirror Proxy** built with **FastAPI**. It helps bypass network restrictions and provides faster access to Docker images by intelligently routing requests to healthy mirrors.

You can:
- **Directly** use a hosted mirror.
- **Deploy on your own server** using Docker Compose and customize the mirror list.

The system automatically performs health checks on all configured mirrors and redirects Docker Daemon requests to one of the healthy candidates.

---

## 🚀 Quick Start

### Option 1: Using a Hosted Mirror

Edit your Docker Daemon configuration file (e.g., `/etc/docker/daemon.json`):

```json
{
  "registry-mirrors": ["https://your-proxy-domain.com"],
  "insecure-registries": ["https://your-proxy-domain.com"]
}
```

Restart Docker:

```bash
sudo systemctl restart docker
```

---

### Option 2: Deploying Your Own Service

#### 1. Prerequisites

Ensure you have Docker and Docker Compose installed on your server.

#### 2. Clone and Run

```bash
git clone https://github.com/movtigroup/mirro-docker.git
cd mirro-docker
docker-compose up -d --build
```

---

## ⚙️ How it Works

- **Health Check:** The service periodically (default: 60s) checks all mirrors in the list by sending a `GET /v2/` request.
- **Reverse Proxy:** Client requests are routed to one of the healthy mirrors (randomly selected).
- **Streaming:** Responses are streamed to handle large Docker layers without high memory consumption.
- **Failover:** If all mirrors are down, it returns a 503 error.

---

## 🔧 Customizing Mirrors

Edit `proxy_config.py`:

```python
MIRRORS = [
    "https://docker.iranserver.com",
    "https://docker.m.daocloud.io",
    "https://mirror.hetzner.com",
    "https://docker.ovh.net",
    # ... add more
]
```

Restart the service after changes:

```bash
docker-compose restart
```

---

## 🗂 Project Structure

```
.
├── main.py              # FastAPI Application (Proxy logic)
├── proxy_config.py      # Configuration and Mirror list
├── requirements.txt     # Python dependencies
├── Dockerfile           # Docker image definition
├── docker-compose.yml   # Service definition
└── README.md            # Persian Documentation
```

---

## 📄 License

This project is released under the **MIT License**.

---

<div align="center">

**✨ Support us by giving this repository a ⭐️!**

</div>
