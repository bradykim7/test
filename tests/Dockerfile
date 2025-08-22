FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    netcat-openbsd \
    build-essential \
    gcc \
    g++ \
    make \
    libevent-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt .
COPY test_requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r test_requirements.txt

# Copy application code and tests
COPY app/ ./app/
COPY consumer/ ./consumer/
COPY tests/ ./tests/
COPY load_testing/ ./load_testing/
COPY run_tests.sh .
COPY pytest.ini .

# Make test script executable
RUN chmod +x run_tests.sh

# Set Python path to include app directory
ENV PYTHONPATH="${PYTHONPATH}:/app/app"

# Default command to run tests
CMD ["./run_tests.sh", "all"]