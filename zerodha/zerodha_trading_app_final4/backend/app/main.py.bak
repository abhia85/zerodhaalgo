from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
from app.kite_client import KiteClient
from app.data_fetcher import DataFetcher
from app.backtester import Backtester
from app.models_db import init_db, SessionLocal, Strategy
from app.kite_auth_exchange import router as auth_router
from app.config import PAPER_MODE
from app.logger import logger
from app.execution_manager import ExecutionManager
import json

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# initialize DB
init_db()

kite = KiteClient()
fetcher = DataFetcher(kite)
backtester = Backtester(fetcher)

# initialize execution manager with models_db module
import models_db as models_db_module
exec_mgr = ExecutionManager(kite, SessionLocal, models_db_module)

app.include_router(auth_router, prefix="/api")

@app.get("/api/auth/login_url")
def auth_login_url():
    try:
        url = kite.get_login_url()
        return {"login_url": url}
    except Exception as e:
        return {"error": "unable_to_generate_login_url", "detail": str(e)}

@app.get("/api/ping")
def ping():
    return {"ok": True}

@app.get("/api/symbols")
def symbols():
    return fetcher.list_nse_symbols()

@app.get("/api/candles")
def candles(symbol: str, interval: str = "5m", from_ts: Optional[str] = None, to_ts: Optional[str] = None):
    data = fetcher.get_candles(symbol, interval, from_ts, to_ts)
    return {"symbol": symbol, "interval": interval, "candles": data}

class BacktestRequest(BaseModel):
    symbol: str
    interval: str
    from_ts: str
    to_ts: str
    strategy_id: str

@app.post("/api/backtest")
def run_backtest(req: BacktestRequest):
    session = SessionLocal()
    strat = session.query(Strategy).filter(Strategy.id==int(req.strategy_id)).first()
    session.close()
    if not strat:
        raise HTTPException(status_code=404, detail="strategy not found")
    strategy_payload = json.loads(strat.payload)
    res = backtester.run(req.symbol, req.interval, req.from_ts, req.to_ts, strategy_payload)
    return res

@app.post("/api/strategies")
def save_strategy(payload: dict):
    session = SessionLocal()
    s = Strategy(name=payload.get('name','unnamed'), payload=json.dumps(payload))
    session.add(s)
    session.commit()
    session.refresh(s)
    session.close()
    return {"id": s.id}

@app.get("/api/strategies")
def list_strats():
    session = SessionLocal()
    items = session.query(Strategy).all()
    out = [{"id": i.id, "name": i.name} for i in items]
    session.close()
    return out

class StartLiveRequest(BaseModel):
    strategy_id: int
    capital: float
    max_daily_loss: float
    allocation: float = 1.0

@app.post("/api/live/start")
def start_live(req: StartLiveRequest):
    if not kite.is_authenticated():
        raise HTTPException(status_code=401, detail="Zerodha not authenticated")
    session = SessionLocal()
    strat = session.query(Strategy).filter(Strategy.id==req.strategy_id).first()
    session.close()
    if not strat:
        raise HTTPException(status_code=404, detail="strategy not found")
    ok, status = exec_mgr.start_live(req.dict())
    if not ok:
        raise HTTPException(status_code=400, detail=status)
    return {"ok": True, "status": status}

@app.post("/api/live/stop")
def stop_live():
    ok, status = exec_mgr.stop_live()
    if not ok:
        raise HTTPException(status_code=400, detail=status)
    return {"ok": True, "status": status}

@app.get("/api/trades")
def list_trades(limit: int = 100):
    session = SessionLocal()
    from models_db import TradeJournal
    items = session.query(TradeJournal).order_by(TradeJournal.created_at.desc()).limit(limit).all()
    out = []
    for it in items:
        out.append({
            "id": it.id,
            "strategy_id": it.strategy_id,
            "symbol": it.symbol,
            "side": it.side,
            "qty": it.qty,
            "entry_price": it.entry_price,
            "exit_price": it.exit_price,
            "pnl": it.pnl,
            "status": it.status,
            "created_at": it.created_at.isoformat()
        })
    session.close()
    return out

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, log_level="info")
