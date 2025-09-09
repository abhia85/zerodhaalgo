# Dockerfile for nested backend in repo
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# copy nested backend requirements and install
COPY zerodha/zerodha_trading_app_final4/backend/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

# copy the backend (will include the `app` package folder)
COPY zerodha/zerodha_trading_app_final4/backend /app

EXPOSE 8000

# Run uvicorn using PORT from environment (Render sets $PORT)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
