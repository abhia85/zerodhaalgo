FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

RUN apt-get update 
    && apt-get install -y --no-install-recommends 
       build-essential 
       gcc 
       libpq-dev 
       libffi-dev 
       libssl-dev 
       pkg-config 
       libfreetype6-dev 
       libpng-dev 
       python3-dev 
       git 
    && rm -rf /var/lib/apt/lists/*

COPY zerodha/zerodha_trading_app_final4/backend/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel 
    && pip install --no-cache-dir -r /app/requirements.txt

COPY zerodha/zerodha_trading_app_final4/backend /app

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port "]
