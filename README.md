<div align="center">

# 🐳 Docker Mirror Proxy ایران

**پراکسی هوشمند میرور داکر برای اینترنت ملی و شرایط قطعی**

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green?logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)
![CI/CD](https://github.com/movtigroup/mirro-docker/actions/workflows/docker-publish.yml/badge.svg)

[English](README.en.md) | [中文](README.zh.md)

</div>

---

## 📋 معرفی

این مخزن شامل **کد سرویس پراکسی هوشمند میرور داکر** است که با **FastAPI** نوشته شده است. این سرویس به صورت خودکار بین لایه‌های مختلف میرور (ایران، چین، اروپا و آمریکا) سوئیچ می‌کند تا بهترین سرعت و پایداری را فراهم کند.

### قابلیت‌های کلیدی:
- **انتخاب لایه‌بندی شده (Tiered):** اولویت‌بندی هوشمند بین Tier 1، میرورهای داخلی و میرورهای جهانی (Tier 2).
- **پشتیبانی از GPG و پکیج‌ها:** قابلیت پراکسی کردن درخواست‌های کلید GPG و مخازن نصب داکر (apt/yum) به میرورهای پرسرعت (Tsinghua, Aliyun, Hetzner, OVH).
- **بررسی سلامت (Health Check):** تست دوره‌ای میرورها برای اطمینان از در دسترس بودن.
- **پاسخ جریانی (Streaming):** انتقال بهینه لایه‌های سنگین داکر بدون اشغال حافظه سرور.

---

## 🚀 شروع سریع

### گزینه اول: استفاده از میرور میزبانی شده (پیشنهادی)

فایل تنظیمات Docker Daemon را ویرایش کنید:

```json
{
  "registry-mirrors": ["https://docker.ththt.ir"],
  "insecure-registries": ["https://docker.ththt.ir"]
}
```

داکر را ریستارت کنید:

```bash
sudo systemctl restart docker
```

---

### گزینه دوم: اجرای سرویس روی سرور شخصی

#### ۱. کلون کردن مخزن و اجرا

```bash
git clone https://github.com/movtigroup/mirro-docker.git
cd mirro-docker
docker-compose up -d --build
```

#### ۲. تنظیمات شخصی

فایل `proxy_config.py` را برای لایه‌بندی میرورها ویرایش کنید:

```python
TIER1_MIRRORS = [...]
IRANIAN_MIRRORS = [...]
TIER2_MIRRORS = [...]
PACKAGE_MIRRORS = [...]
```

---

## ⚙️ نحوه کار

- **Health Check:** در پس‌زمینه، سرویس به طور دوره‌ای همه میرورها را بررسی می‌کند.
- **منطق اولویت‌بندی:** ابتدا Tier 1، سپس میرورهای ایرانی و در نهایت Tier 2 (چین و جهانی) بررسی می‌شوند.
- **پراکسی پکیج:** درخواست‌های مربوط به نصب داکر (مانند `linux/ubuntu` یا `gpg`) به صورت خودکار به میرورهای مخصوص پکیج هدایت می‌شوند.

---

## 📄 مجوز

این پروژه تحت **MIT License** منتشر شده است. استفاده، تغییر و توزیع آزاد است.

---

<div align="center">

**✨ با ⭐️ دادن به این مخزن، از ما حمایت کنید!**

</div>
