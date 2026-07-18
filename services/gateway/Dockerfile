FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY assets/ assets/
COPY migrations/ migrations/
COPY shared/ shared/
COPY services/ services/
RUN useradd -m -u 1000 appuser
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python3 -c "import httpx; httpx.get('http://localhost:8000/health', timeout=3).raise_for_status()"
CMD ["uvicorn", "services.gateway.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
