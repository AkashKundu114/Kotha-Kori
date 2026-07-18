FROM python:3.11-slim
RUN apt-get update && apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY assets/ assets/
COPY migrations/ migrations/
COPY shared/ shared/
COPY services/ services/
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
CMD ["celery", "-A", "services.orchestrator.celery_entrypoint", "worker", "--loglevel=info", "--concurrency=4"]
