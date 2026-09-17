FROM python:3.11-slim

WORKDIR /app

# وابستگی‌ها رو جدا کپی می‌کنیم تا وقتی فقط کد عوض می‌شه، این لایه از کش داکر استفاده بشه
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# پوشه‌های داده/لاگ که قبلاً لوکال ساخته می‌شدن؛ اینجا هم از قبل بسازیمشون
RUN mkdir -p database logs reports

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
