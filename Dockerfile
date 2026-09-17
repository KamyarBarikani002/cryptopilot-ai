FROM python:3.11-slim

WORKDIR /app

# وابستگی‌ها رو جدا کپی می‌کنیم تا وقتی فقط کد عوض می‌شه، این لایه از کش داکر استفاده بشه
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# پوشه‌های داده/لاگ که قبلاً لوکال ساخته می‌شدن؛ اینجا هم از قبل بسازیمشون
RUN mkdir -p database logs reports

# پورت ثابت ۸۵۰۱ عمدی است: پروکسی Railway برای این سرویس روی همین پورت تنظیم
# شده. یک‌بار این رو به ${PORT} تغییر دادیم (که Railway مقدار 8080 براش تزریق
# می‌کند) و نتیجه‌اش 502 شد، چون اپ روی 8080 لیسن می‌کرد ولی ترافیک به 8501
# می‌رفت. اگر روی هاست دیگری اجرا شد که پورت داینامیک می‌خواهد، یا این خط را
# به ${PORT:-8501} برگردان و target port را هم همان‌جا اصلاح کن.
EXPOSE 8501

# نکته: HEALTHCHECK قبلی با curl بود که توی ایمیج python:3.11-slim نصب نیست و
# همیشه fail می‌شد، برای همین حذف شده؛ Railway خودش healthcheck جدا دارد.
CMD streamlit run dashboard.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
