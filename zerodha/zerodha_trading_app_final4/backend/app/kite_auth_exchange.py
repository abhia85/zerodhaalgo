
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import os
import requests
import urllib.parse

router = APIRouter()

API_KEY = os.getenv('KITE_API_KEY','')
API_SECRET = os.getenv('KITE_API_SECRET','')
REDIRECT_URI = os.getenv('KITE_REDIRECT_URI','http://localhost:8000/api/auth/callback')

# Exchange endpoint per Kite Connect docs:
# POST https://api.kite.trade/session/token?api_key=API_KEY&request_token=REQUEST_TOKEN&checksum=SHA256(request_token+API_SECRET+API_KEY)
# For safety we implement a server-side exchange that expects request_token from the redirect and performs the exchange.

def _compute_checksum(request_token):
    import hashlib
    payload = request_token + API_SECRET + API_KEY
    return hashlib.sha256(payload.encode()).hexdigest()

@router.post('/auth/exchange')
def auth_exchange(payload: dict):
    # payload should contain {"request_token": "..."}
    request_token = payload.get('request_token')
    if not request_token:
        return JSONResponse({'error':'request_token missing'}, status_code=400)
    if not API_KEY or not API_SECRET:
        return JSONResponse({'error':'api key/secret not configured on server'}, status_code=500)
    checksum = _compute_checksum(request_token)
    url = f"https://api.kite.trade/session/token?api_key={API_KEY}&request_token={request_token}&checksum={checksum}"
    try:
        resp = requests.post(url, timeout=10)
        data = resp.json()
        if 'data' in data and 'access_token' in data['data']:
            access_token = data['data']['access_token']
            # expires_at may be available in response metadata; store token via KiteClient
            from app.kite_client import KiteClient
            kc = KiteClient()
            kc.set_token(access_token, expires_in_seconds=None)  # expiry handling optional
            return {'ok': True}
        else:
            return JSONResponse({'error':'exchange_failed', 'detail': data}, status_code=400)
    except Exception as e:
        return JSONResponse({'error':'network', 'detail': str(e)}, status_code=500)
