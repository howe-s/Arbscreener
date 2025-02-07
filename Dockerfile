FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV FLASK_ENV=production
ENV RAILWAY_ENVIRONMENT=production

# Run the application with environment variable PORT
CMD gunicorn --bind 0.0.0.0:$PORT --workers 4 --threads 2 --timeout 120 --log-level debug app:app 