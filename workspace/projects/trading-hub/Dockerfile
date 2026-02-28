# Trading Hub Dockerfile
# Python 3.11-slim based image for the trading bot management dashboard

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# non-root 사용자 생성 및 전환 (보안: 컨테이너를 root로 실행하지 않음)
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser \
    && mkdir -p /app/data && chown -R appuser:appgroup /app
USER appuser

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
