# Ảnh chạy pipeline dữ liệu hằng ngày (run_daily_crawl.py): Python 3.11 + Chromium headless.
# Ảnh chỉ chứa thư viện; mã (crawlers/, serving/) và dữ liệu (data/, raw/) gắn từ thư mục gốc repo lúc chạy,
# xem service "pipeline" trong webapp/docker-compose.yml.

FROM python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-daily.txt /tmp/requirements-daily.txt
RUN pip install --no-cache-dir -r /tmp/requirements-daily.txt

COPY chromium-headless /usr/local/bin/chromium-headless
RUN chmod 755 /usr/local/bin/chromium-headless \
    && useradd --create-home --uid 1000 pipeline

ENV EDGE_PATH=/usr/local/bin/chromium-headless \
    TZ=Asia/Ho_Chi_Minh \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
USER pipeline
WORKDIR /work
CMD ["python", "run_daily_crawl.py"]
