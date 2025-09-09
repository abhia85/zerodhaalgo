
import os
import threading
import time
import sqlite3
from typing import Optional
from cryptography.fernet import Fernet
from models_db import SessionLocal, TokenStore, TradeJournal, DailyLoss
import requests
from datetime import datetime, timedelta
import json

DB_PATH = os.getenv("TOKEN_DB_PATH", "./kite_tokens.sqlite")
PAPER_MODE = os.getenv("PAPER_MODE", "true").lower() in ("1","true","yes")
API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")
MAX_DAILY_LOSS = float(os.getenv('MAX_DAILY_LOSS', '0'))  # 0 disables cap

class KiteClient:
    def __init__(self):
        self.api_key = API_KEY
        self.api_secret = API_SECRET
        self._access_token = None
        self._expires_at = None
        self.refresh_lock = threading.Lock()
        self.live_worker = None
        self.fernet = self._load_or_create_key()
        # try load from DB via models_db
        tok, exp = self._load_token_from_db()
        if tok:
            self._access_token = tok
            self._expires_at = exp

    def _load_or_create_key(self):
        key = os.getenv("KITE_ENC_KEY")
        if not key:
            key = Fernet.generate_key().decode()
            print("Generated KITE_ENC_KEY (save this securely):", key)
        return Fernet(key.encode())

    def _save_token_to_db_models(self, name: str, token: str, expires_at: Optional[datetime]=None):
        session = SessionLocal()
        ts = session.query(TokenStore).filter(TokenStore.name==name).first()
        if not ts:
            ts = TokenStore(name=name, token=self.fernet.encrypt(token.encode()).decode(), expires_at=expires_at)
            session.add(ts)
        else:
            ts.token = self.fernet.encrypt(token.encode()).decode()
            ts.expires_at = expires_at
        session.commit()
        session.close()

    def _load_token_from_db(self):
        session = SessionLocal()
        ts = session.query(TokenStore).filter(TokenStore.name=='access_token').first()
        if not ts:
            session.close()
            return None, None
        try:
            dec = self.fernet.decrypt(ts.token.encode()).decode()
            exp = ts.expires_at
            session.close()
            return dec, exp
        except Exception as e:
            session.close()
            print("Failed to decrypt token:", e)
            return None, None

    def is_authenticated(self):
        if not self._access_token:
            return False
        if self._expires_at and datetime.utcnow() > self._expires_at:
            return False
        return True

    def set_token(self, access_token: str, expires_in_seconds: Optional[int]=None):
        self._access_token = access_token
        if expires_in_seconds:
            self._expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in_seconds))
        else:
            self._expires_at = None
        # persist encrypted token into models DB
        self._save_token_to_db_models('access_token', access_token, self._expires_at)

    def refresh_token_if_needed(self):
        # Check expiry and either re-run auth flow or raise. If token expired, return False and expose a login URL.
        try:
            if self._expires_at and datetime.utcnow() > self._expires_at:
                print("Access token expired - needs re-authentication")
                return False
            return True
        except Exception as e:
            print('refresh check error', e)
            return False

    def get_login_url(self, redirect_uri=None):
        """Return the Kite Connect login URL for manual re-authentication.
        The frontend can open this URL so the user can login and obtain a request_token for /api/auth/exchange.
        """
        api_key = os.getenv('KITE_API_KEY')
        redirect = redirect_uri or os.getenv('KITE_REDIRECT_URI','http://localhost:8000/api/auth/callback')
        if not api_key:
            raise RuntimeError('KITE_API_KEY not configured')
        import urllib.parse
        login_url = f"https://kite.zerodha.com/connect/login?v=3&api_key={api_key}&redirect_uri={urllib.parse.quote(redirect)}"
        return login_url

    def start_live_run(self, start_live_request):
        if self.live_worker and self.live_worker.is_alive():
            return
        from workers import LiveWorker
        self._stop_flag = threading.Event()
        self.live_worker = LiveWorker(self, start_live_request)
        self.live_worker.start()

    def _daily_loss_total(self):
        session = SessionLocal()
        today = datetime.utcnow().date()
        # sum pnl of CLOSED trades for today
        total = session.query(TradeJournal).filter(TradeJournal.created_at >= datetime.combine(today, datetime.min.time())).with_entities(func.sum(TradeJournal.pnl)).scalar()
        session.close()
        return float(total or 0.0)

    def _validate_order(self, order_payload):
        # Basic safety checks to prevent catastrophic orders
        max_qty = int(os.getenv('MAX_QTY_PER_ORDER', '1000'))
        qty = int(order_payload.get('quantity', 0))
        if qty <= 0 or qty > max_qty:
            return False, f'qty {qty} invalid or exceeds max {max_qty}'
        symbol = order_payload.get('tradingsymbol') or order_payload.get('symbol')
        if not symbol:
            return False, 'symbol missing'
        allowed_suffix = os.getenv('ALLOWED_SYMBOL_SUFFIX', '.NS')
        if allowed_suffix and not symbol.endswith(allowed_suffix):
            return False, f'symbol {symbol} not allowed'
        # Daily loss enforcement
        if MAX_DAILY_LOSS > 0:
            current_loss = self._daily_loss_total()
            if current_loss >= MAX_DAILY_LOSS:
                return False, f'daily loss limit reached: {current_loss} >= {MAX_DAILY_LOSS}'
        return True, 'ok'

    def _place_order(self, order_payload):
        ok, reason = self._validate_order(order_payload)
        if not ok:
            return {'error': 'validation_failed', 'reason': reason}
        if PAPER_MODE:
            # persist simulated trade into DB
            session = SessionLocal()
            try:
                tj = TradeJournal(
                    strategy_id=order_payload.get('strategy_id'),
                    symbol=order_payload.get('tradingsymbol') or order_payload.get('symbol'),
                    side=order_payload.get('side','BUY'),
                    qty=int(order_payload.get('quantity',0)),
                    entry_price=float(order_payload.get('price',0.0)),
                    status='SIMULATED',
                    pnl=0.0
                )
                session.add(tj)
                session.commit()
                session.refresh(tj)
                # update daily loss if negative pnl (none for simulated entry)
                session.close()
                return {'status':'simulated','order_id': f'PAPER-{tj.id}', 'trade_id': tj.id}
            except Exception as e:
                session.close()
                return {'error':'db', 'detail': str(e)}
        # Real order via Kite Connect REST
        headers = {"Authorization": f"token {self.api_key}:{self._access_token}"}
        try:
            resp = requests.post("https://api.kite.trade/orders/regular", data=order_payload, headers=headers, timeout=10)
            return resp.json()
        except Exception as e:
            return {'error': 'network', 'detail': str(e)}

    def stop_live_run(self):
        if hasattr(self, 'live_worker') and self.live_worker:
            self.live_worker.stop()
            self.live_worker = None
