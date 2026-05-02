FROM python:3.11-slim

# تنظیمات محیطی
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ایجاد و جابجایی به دایرکتوری کاری
WORKDIR /app

# نصب وابستگی‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی سورس کد
COPY . .

# پورت استفاده شده توسط uvicorn
EXPOSE 8080

# اجرای اپلیکیشن
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
