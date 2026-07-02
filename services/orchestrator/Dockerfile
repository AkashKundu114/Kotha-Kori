FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ shared/
COPY services/ services/
CMD ["celery", "-A", "services.orchestrator.celery_entrypoint", "worker", "--loglevel=info"]
