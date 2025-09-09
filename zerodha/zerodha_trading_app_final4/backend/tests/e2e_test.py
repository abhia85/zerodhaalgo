
# e2e_test.py - end-to-end test for the app
# Precondition: backend running on http://localhost:8000 and PAPER_MODE=true
import requests, time, os, sys

API = os.getenv('API_URL','http://localhost:8000/api')

def create_strategy():
    payload = {'name':'E2E EMA', 'type':'ema_cross', 'fast':5, 'slow':13, 'symbol':'RELIANCE.NS', 'interval':'1d'}
    r = requests.post(API + '/strategies', json=payload)
    print('create strategy', r.status_code, r.text)
    return int(r.json()['id'])

def run_backtest(sid):
    payload = {'symbol':'RELIANCE.NS','interval':'1d','from_ts':'2024-01-01','to_ts':'2024-06-01','strategy_id':str(sid)}
    r = requests.post(API + '/backtest', json=payload)
    print('backtest', r.status_code)
    data = r.json()
    print('metrics keys:', list(data.keys()))
    return data

def start_live(sid):
    payload = {'strategy_id': int(sid), 'capital':100000, 'max_daily_loss':10000, 'allocation':1}
    r = requests.post(API + '/live/start', json=payload)
    print('start live', r.status_code, r.text)
    return r.ok

def list_trades():
    r = requests.get(API + '/trades')
    print('trades', r.status_code, r.text)
    return r.json()

if __name__ == '__main__':
    sid = create_strategy()
    bt = run_backtest(sid)
    ok = start_live(sid)
    if not ok:
        print('live did not start, ensure kite is authenticated (PAPER_MODE sim still works).')
    print('waiting 8 seconds for worker to simulate trades...')
    time.sleep(8)
    trades = list_trades()
    print('found', len(trades), 'trades')
    if len(trades) == 0:
        print('No trades yet; ensure worker is running and candles available.')
    else:
        print('E2E test success')
