FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY consumer/ ./consumer/

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD ps aux | grep -v grep | grep "python consumer/main.py" || exit 1

# Run the consumer
CMD ["python", "consumer/main.py"]