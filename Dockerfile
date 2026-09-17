FROM python:3.11-slim

WORKDIR /app

# وابستگی‌ها رو جدا کپی می‌کنیم تا وقتی فقط کد عوض می‌شه، این لایه از کش داکر استفاده بشه
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# پوشه‌های داده/لاگ که قبلاً لوکال ساخته می‌شدن؛ اینجا هم از قبل بسازیمشون
RUN mkdir -p database logs reports

EXPOSE 8501

# شل‌فرم (نه exec-form) استفاده می‌شه تا ${PORT} که سرویس‌هایی مثل Railway تزریق
# می‌کنن جایگزین بشه؛ اگر تعریف نشده باشه همون 8501 پیش‌فرض می‌مونه.
# نکته: HEALTHCHECK قبلی با curl بود که توی ایمیج python:3.11-slim نصب نیست و
# همیشه fail می‌شد، برای همین حذف شد؛ Railway خودش healthcheck جدا داره.
CMD streamlit run dashboard.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true
