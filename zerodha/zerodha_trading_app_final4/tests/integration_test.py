
# Integration test script (PAPER_MODE)
# Run this script after starting the backend (uvicorn main:app)
# It will:
# 1) Create a simple EMA strategy via /api/strategies
# 2) Start a live run via /api/live/start (PAPER_MODE must be true)
# 3) Wait some seconds and check that trades were simulated in the DB.

import requests
import time
import os

API = os.getenv('API_URL','http://localhost:8000/api')

# 1) Create strategy
payload = {'name':'EMA Test', 'type':'ema_cross', 'fast':5, 'slow':13, 'symbol':'RELIANCE.NS', 'interval':'1d'}
r = requests.post(API + '/strategies', json=payload)
print('Create strategy:', r.status_code, r.text)
sid = r.json().get('id')

# 2) Start live
start_payload = {'strategy_id': int(sid), 'capital':100000, 'max_daily_loss':2000, 'allocation':1}
r2 = requests.post(API + '/live/start', json=start_payload)
print('Start live:', r2.status_code, r2.text)

# 3) Wait and then verify trades
time.sleep(10)
r3 = requests.get(API + '/strategies')
print('Strategies:', r3.status_code, r3.text)
print('Check trades in DB manually (or add endpoint to list trades).')
