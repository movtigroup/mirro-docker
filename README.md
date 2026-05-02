
<div align="center">

# 🐳 Docker Mirror Proxy ایران

**پراکسی هوشمند میرور داکر برای اینترنت ملی و شرایط قطعی**

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green?logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)

</div>

---

## 📋 معرفی

این مخزن شامل **کد سرویس پراکسی هوشمند میرور داکر** است که با **FastAPI** نوشته شده و در سرور **https://docker.ththt.ir** به صورت آماده در دسترس است.
شما می‌توانید:

- **مستقیم** از میرور میزبانی شده https://docker.ththt.ir استفاده کنید (بدون نیاز به راه‌اندازی سرویس).
- **کد را در سرور خودتان** با Docker Compose اجرا کنید و لیست میرورها را شخصی‌سازی کنید.

در هر دو حالت، سیستم به صورت خودکار سلامت میرورها را بررسی کرده و درخواست‌های Docker Daemon را هدایت می‌کند.

---

## 🚀 شروع سریع

### گزینه اول: استفاده از میرور میزبانی شده (پیشنهادی)

فایل تنظیمات Docker Daemon را ویرایش کنید:

```bash
sudo nano /etc/docker/daemon.json
```

محتوای زیر را قرار دهید:

```json
{
  "registry-mirrors": ["https://docker.ththt.ir"],
  "insecure-registries": ["https://docker.ththt.ir"]
}
```

> اگر میرور شما از گواهی معتبر استفاده می‌کند (`https` معتبر)، خط `insecure-registries` اختیاری است. اما برای اطمینان در محیط‌های خاص، اضافه شده است.

داکر را ریستارت کنید:

```bash
sudo systemctl restart docker
```

حالا دستور `docker pull` از این میرور استفاده می‌کند.

---

### گزینه دوم: اجرای سرویس روی سرور شخصی

#### ۱. نصب Docker

از اسکریپت ساده مخزن [movtigroup/docker](https://github.com/movtigroup/docker) استفاده کنید (طراحی شده برای ایران):

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/movtigroup/docker/master/install.sh)"
```

#### ۲. کلون کردن مخزن و اجرا

```bash
git clone https://github.com/movtigroup/mirro-docker.git
cd mirro-docker
docker-compose up -d --build
```

#### ۳. تنظیم Docker برای استفاده از پراکسی محلی

```json
{
  "registry-mirrors": ["https://docker.ththt.ir"],
  "insecure-registries": ["https://docker.ththt.ir"]
}
```

سپس `sudo systemctl restart docker`.

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
    "https://docker.arvancloud.ir",
    "https://mirror2.chabokan.net",
    "https://docker.derak.cloud",
    "https://docker.ththt.ir",   # میرور پیش‌فرض میزبانی شده
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
├── main.py              # اپلیکیشن FastAPI (پراکسی)
├── proxy_config.py      # تنظیمات و لیست میرورها
├── requirements.txt     # وابستگی‌های پایتون
├── Dockerfile           # ساخت ایمج داکر
├── docker-compose.yml   # تعریف سرویس
├── .dockerignore        # فایل‌های نادیده گرفته شده در داکر
└── README.md            # همین فایل
```

---

## 🌐 مخزن رسمی

برای مشاهده آخرین تغییرات و مشارکت:

👉 **https://github.com/movtigroup/mirro-docker**

---

## 📄 مجوز

این پروژه تحت **MIT License** منتشر شده است. استفاده، تغییر و توزیع آزاد است.

---

<div align="center">

**✨ با ⭐️ دادن به این مخزن، از ما حمایت کنید!**

</div>
```
