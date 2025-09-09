# Use official Python image
FROM python:3.11-slim

# Avoid generating .pyc files and make logs immediate
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install system deps needed to build some wheels and for libpq
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install (paths reflect nested repo layout)
COPY zerodha/zerodha_trading_app_final4/backend/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

# Copy backend app code into /app
COPY zerodha/zerodha_trading_app_final4/backend /app

# Expose port (informational)
EXPOSE 8000

# Run uvicorn using package path; honor Render's $PORT if provided
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
