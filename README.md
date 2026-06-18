<div align="center">

# 🐳 Docker Mirror Proxy ایران

**پراکسی هوشمند میرور داکر برای اینترنت ملی و شرایط قطعی**

[![Publish Docker image](https://github.com/movtigroup/mirro-docker/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/movtigroup/mirro-docker/actions/workflows/docker-publish.yml)
![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green?logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)

[فارسی](README.md) | [English](README.en.md) | [简体中文](README.zh.md)

</div>

---

## 📋 معرفی

این مخزن شامل **کد سرویس پراکسی هوشمند میرور داکر** است که با **FastAPI** نوشته شده و به صورت هوشمند درخواست‌ها را به سمت میرورهای سالم هدایت می‌کند.

شما می‌توانید:

- **مستقیم** از یک میرور میزبانی شده استفاده کنید.
- **کد را در سرور خودتان** با Docker Compose اجرا کنید و لیست میرورها را شخصی‌سازی کنید.

در هر دو حالت، سیستم به صورت خودکار سلامت میرورها را بررسی کرده و درخواست‌های Docker Daemon را هدایت می‌کند.

---

## 🚀 شروع سریع

### گزینه اول: استفاده از میرور میزبانی شده (پیشنهادی)

فایل تنظیمات Docker Daemon را ویرایش کنید (مثلاً `/etc/docker/daemon.json`):

```json
{
  "registry-mirrors": ["https://docker.ththt.ir"],
  "insecure-registries": ["https://docker.ththt.ir"]
}
```

> **نکته:** آدرس `https://docker.ththt.ir` یک مثال است. از آدرس دامنه خودتان استفاده کنید.

داکر را ریستارت کنید:

```bash
sudo systemctl restart docker
```

---

### گزینه دوم: اجرای سرویس روی سرور شخصی

#### ۱. پیش‌نیازها

مطمئن شوید Docker و Docker Compose روی سرور شما نصب است.

#### ۲. کلون کردن مخزن و اجرا

```bash
git clone https://github.com/movtigroup/mirro-docker.git
cd mirro-docker
docker-compose up -d --build
```

---

## ⚙️ نحوه کار

- **Health Check:** در پس‌زمینه، سرویس به طور دوره‌ای (پیش‌فرض هر ۶۰ ثانیه) همه میرورهای لیست را با ارسال درخواست `GET /v2/` بررسی می‌کند.
- **پراکسی معکوس:** درخواست کلاینت به یکی از میرورهای سالم (تصادفی) هدایت می‌شود.
- **Stream:** پاسخ به صورت جریانی برگردانده می‌شود تا لایه‌های حجیم داکر بدون اشغال حافظه منتقل شوند.
- **Failover:** اگر همه میرورها قطع باشند، خطای ۵۰۳ برگردانده می‌شود.

---

## 🔧 شخصی‌سازی لیست میرورها

فایل `proxy_config.py` را ویرایش کنید:

```python
MIRRORS = [
    "https://docker.iranserver.com",
    "https://docker.abrha.net",
    "https://mirror.hetzner.com",
    "https://docker.ovh.net",
    # ... موارد بیشتر اضافه کنید
]
```

پس از تغییر، سرویس را ری‌استارت کنید:

```bash
docker-compose restart
```

---

## 🗂 ساختار فایل‌ها

```
.
├── main.py              # اپلیکیشن FastAPI (منطق پراکسی)
├── proxy_config.py      # تنظیمات و لیست میرورها
├── requirements.txt     # وابستگی‌های پایتون
├── Dockerfile           # ساخت ایمج داکر
├── docker-compose.yml   # تعریف سرویس
└── README.md            # همین فایل
```

---

## 📄 مجوز

این پروژه تحت **MIT License** منتشر شده است. استفاده، تغییر و توزیع آزاد است.

---

<div align="center">

**✨ با ⭐️ دادن به این مخزن، از ما حمایت کنید!**

</div>
