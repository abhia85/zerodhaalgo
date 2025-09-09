# Use official Python image
FROM python:3.11-slim

# Avoid generating .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/app

# Set workdir
WORKDIR /app

# Install system deps for some packages if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY zerodha/zerodha_trading_app_final4/backend/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

# Copy backend app code
COPY zerodha/zerodha_trading_app_final4/backend /app

# Expose port
EXPOSE 8000

# Set working dir to the app package folder where main.py lives
WORKDIR /app/app

# Start uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
