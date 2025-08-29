FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for snappy compression
RUN apt-get update && apt-get install -y \
    libsnappy-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ .

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application with Gunicorn + Uvicorn workers for high concurrency
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--max-requests", "10000", "--max-requests-jitter", "1000"]