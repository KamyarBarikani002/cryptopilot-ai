FROM python:3.11-slim

WORKDIR /app

# وابستگی‌ها رو جدا کپی می‌کنیم تا وقتی فقط کد عوض می‌شه، این لایه از کش داکر استفاده بشه
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# پوشه‌های داده/لاگ که قبلاً لوکال ساخته می‌شدن؛ اینجا هم از قبل بسازیمشون
RUN mkdir -p database logs reports

# پورت: اگر هاست متغیر PORT را تزریق کند (Render مقدار 10000 می‌دهد) روی همان
# گوش می‌دهد، وگرنه 8501. نکته‌ی Railway: آنجا PORT=8080 تزریق می‌شود ولی
# target port دامنه روی 8501 تنظیم شده بود؛ اگر دوباره روی Railway دیپلوی شد،
# یک متغیر PORT=8501 روی سرویس بگذار تا این دو یکی باشند (وگرنه 502 می‌دهد).
EXPOSE 8501

# نکته: HEALTHCHECK قبلی با curl بود که توی ایمیج python:3.11-slim نصب نیست و
# همیشه fail می‌شد، برای همین حذف شده؛ Railway خودش healthcheck جدا دارد.
CMD streamlit run dashboard.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true
