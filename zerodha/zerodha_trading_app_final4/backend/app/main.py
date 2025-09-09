"""
Robust FastAPI module for Render/Docker.

Key design:
 - Expose `app` at module scope immediately so Uvicorn can import it.
 - Perform potentially-failing initialisation (DB, Kite client) in startup event.
 - Endpoints access app.state.<component> and return graceful errors (503) if missing.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
import json
import traceback

logger = logging.getLogger("uvicorn.error")

# application object is created at import-time (so uvicorn import works)
app = FastAPI(title="zerodha-backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# initialize safe state placeholders
app.state.kite = None
app.state.fetcher = None
app.state.backtester = None
app.state.db_inited = False

@app.on_event("startup")
async def startup_event():
    """
    Try to initialize optional components on startup.
    All failures are logged but do not crash the process.
    """
    logger.info("Startup: initializing optional components")
    # 1) init DB (if available)
    try:
        from app.models_db import init_db  # import here to avoid import-time failures
        init_db()
        app.state.db_inited = True
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"DB init skipped or failed: {e}")
        logger.debug(traceback.format_exc())

    # 2) Create KiteClient, DataFetcher, Backtester if available
    try:
        from app.kite_client import KiteClient
        from app.data_fetcher import DataFetcher
        from app.backtester import Backtester
        kite = KiteClient()
        fetcher = DataFetcher(kite)
        backtester = Backtester(fetcher)
        app.state.kite = kite
        app.state.fetcher = fetcher
        app.state.backtester = backtester
        logger.info("KiteClient / DataFetcher / Backtester initialised")
    except Exception as e:
        logger.warning(f"Kite/backtester init failed: {e}")
        logger.debug(traceback.format_exc())

    # 3) Include auth router if module available (safe include)
    try:
        from app.kite_auth_exchange import router as auth_router
        # include router only if not already added
        app.include_router(auth_router, prefix="/api")
        logger.info("Included kite_auth_exchange router")
    except Exception as e:
        logger.info("Auth router not included (module missing or failed to import): %s", str(e))


# Small helpers to get components (raise 503 if not ready)
def _get_kite():
    k = getattr(app.state, "kite", None)
    if not k:
        raise HTTPException(status_code=503, detail="Kite client not available")
    return k

def _get_fetcher():
    f = getattr(app.state, "fetcher", None)
    if not f:
        raise HTTPException(status_code=503, detail="DataFetcher not available")
    return f

def _get_backtester():
    b = getattr(app.state, "backtester", None)
    if not b:
        raise HTTPException(status_code=503, detail="Backtester not available")
    return b


@app.get("/")
def root():
    """Root friendly endpoint so `/` is not 404."""
    return {"ok": True, "service": "zerodha-backend", "db_init": app.state.db_inited}


@app.get("/api/ping")
def ping():
    return {"ok": True}


@app.get("/api/symbols")
def symbols():
    """
    Return a list of symbols. If fetcher is missing, return a small safe fallback.
    """
    try:
        f = _get_fetcher()
        return f.list_nse_symbols()
    except HTTPException:
        # safe fallback
        return ["NIFTY 50", "BANKNIFTY", "RELIANCE.NS", "TCS.NS", "INFY.NS"]
    except Exception:
        logger.exception("symbols endpoint error")
        return []


@app.get("/api/candles")
def candles(symbol: str, interval: str = "5m", from_ts: Optional[str] = None, to_ts: Optional[str] = None):
    try:
        f = _get_fetcher()
        data = f.get_candles(symbol, interval, from_ts, to_ts)
        return {"symbol": symbol, "interval": interval, "candles": data}
    except HTTPException:
        return {"symbol": symbol, "interval": interval, "candles": []}
    except Exception:
        logger.exception("candles endpoint error")
        return {"symbol": symbol, "interval": interval, "candles": []}


# --- Backtest / strategy endpoints (use DB only when available) ---
class BacktestRequest(BaseModel):
    symbol: str
    interval: str
    from_ts: str
    to_ts: str
    strategy_id: str

@app.post("/api/backtest")
def run_backtest(req: BacktestRequest):
    # import DB models lazily and fail gracefully if DB not available
    try:
        from app.models_db import init_db, SessionLocal, Strategy
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB not available: {e}")

    session = SessionLocal()
    try:
        strat = session.query(Strategy).filter(Strategy.id == int(req.strategy_id)).first()
    except Exception as e:
        session.close()
        logger.exception("DB query failed")
        raise HTTPException(status_code=500, detail="DB query failed")
    session.close()
    if not strat:
        raise HTTPException(status_code=404, detail="strategy not found")
    try:
        strategy_payload = json.loads(strat.payload)
    except Exception:
        strategy_payload = {}
    bt = _get_backtester()
    res = bt.run(req.symbol, req.interval, req.from_ts, req.to_ts, strategy_payload)
    return res


@app.post("/api/strategies")
def save_strategy(payload: dict):
    try:
        from app.models_db import SessionLocal, Strategy
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB not available: {e}")

    session = SessionLocal()
    s = Strategy(name=payload.get("name", "unnamed"), payload=json.dumps(payload))
    session.add(s)
    session.commit()
    session.refresh(s)
    session.close()
    return {"id": s.id}


@app.get("/api/strategies")
def list_strats():
    try:
        from app.models_db import SessionLocal
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB not available: {e}")

    session = SessionLocal()
    items = session.query().all() if False else session.query  # safe no-op placeholder
    # We'll attempt a proper query and handle exceptions
    try:
        items = session.query(__import__("app.models_db", fromlist=["Strategy"]).Strategy).all()
        out = [{"id": i.id, "name": i.name} for i in items]
    except Exception:
        logger.exception("Listing strategies failed")
        out = []
    session.close()
    return out


class StartLiveRequest(BaseModel):
    strategy_id: int
    capital: float
    max_daily_loss: float
    allocation: float = 1.0

@app.post("/api/live/start")
def start_live(req: StartLiveRequest):
    try:
        kite = _get_kite()
    except HTTPException as he:
        raise he
    # validate strategy exists (DB)
    try:
        from app.models_db import SessionLocal
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB not available: {e}")

    session = SessionLocal()
    try:
        Strategy = __import__("app.models_db", fromlist=["Strategy"]).Strategy
        strat = session.query(Strategy).filter(Strategy.id == req.strategy_id).first()
    finally:
        session.close()
    if not strat:
        raise HTTPException(status_code=404, detail="strategy not found")
    # start live run (Kite client must implement start_live_run)
    try:
        kite.start_live_run(req)
        return {"ok": True, "status": "started"}
    except Exception as e:
        logger.exception("start_live failed")
        raise HTTPException(status_code=500, detail=f"start_live failed: {e}")


@app.post("/api/live/stop")
def stop_live():
    try:
        kite = _get_kite()
    except HTTPException as he:
        raise he
    try:
        kite.stop_live_run()
        return {"ok": True, "status": "stopped"}
    except Exception as e:
        logger.exception("stop_live failed")
        raise HTTPException(status_code=500, detail=f"stop_live failed: {e}")


@app.get("/api/trades")
def list_trades(limit: int = 100):
    try:
        from app.models_db import SessionLocal, TradeJournal
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB not available: {e}")

    session = SessionLocal()
    try:
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
    except Exception:
        logger.exception("list_trades failed")
        out = []
    session.close()
    return out


if __name__ == "__main__":
    # Allow convenient local run: python main.py
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=10000, log_level="info")
