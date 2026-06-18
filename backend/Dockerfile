FROM python:3.13-slim

WORKDIR /app

# Install runtime deps first for layer caching.
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY app ./app

# SQLite DB + uploaded files live under /data — mount a persistent volume here.
ENV DB_PATH=/data/contracts.db \
    UPLOAD_DIR=/data/uploads
RUN mkdir -p /data/uploads

EXPOSE 8000

# IMPORTANT: a single worker only. The progress store is in-process and the
# analysis runs as an in-process background task, so multiple workers would not
# share state. Scale vertically, not horizontally (see DEPLOYMENT.md).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
