FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ shared/
COPY services/ services/
RUN useradd -m -u 1000 appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "services.gateway.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
