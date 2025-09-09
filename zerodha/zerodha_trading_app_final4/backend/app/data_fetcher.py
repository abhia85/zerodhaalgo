# data_fetcher.py - robust fallback data fetcher
from typing import List, Dict, Optional
from datetime import datetime
import traceback

# optional yfinance fallback
try:
    import yfinance as yf
except Exception:
    yf = None

class DataFetcher:
    def __init__(self, kite_client=None):
        self.kite = kite_client

    def list_nse_symbols(self) -> List[str]:
        try:
            if self.kite and hasattr(self.kite, "get_instruments"):
                instruments = self.kite.get_instruments()
                out = []
                for i in instruments:
                    if isinstance(i, dict):
                        if "tradingsymbol" in i:
                            out.append(i["tradingsymbol"])
                        elif "symbol" in i:
                            out.append(i["symbol"])
                if out:
                    return out
        except Exception:
            pass
        return ["NIFTY 50", "BANKNIFTY", "RELIANCE.NS", "TCS.NS", "INFY.NS"]

    def _canonize_row(self, ts, o, h, l, c, v):
        if isinstance(ts, (int, float)):
            ts_iso = datetime.utcfromtimestamp(ts).isoformat()
        else:
            ts_iso = str(ts)
        return {
            "timestamp": ts_iso,
            "open": float(o),
            "high": float(h),
            "low": float(l),
            "close": float(c),
            "volume": int(v or 0)
        }

    def get_candles(self, symbol: str, interval: str = "5m", from_ts: Optional[str] = None, to_ts: Optional[str] = None) -> List[Dict]:
        # 1) kite client try
        try:
            if self.kite:
                if hasattr(self.kite, "get_candles"):
                    raw = self.kite.get_candles(symbol, interval, from_ts, to_ts)
                    out = []
                    for r in raw or []:
                        if isinstance(r, (list, tuple)) and len(r) >= 6:
                            ts = r[0] / 1000.0 if isinstance(r[0], (int,float)) else r[0]
                            out.append(self._canonize_row(ts, r[1], r[2], r[3], r[4], r[5]))
                        elif isinstance(r, dict):
                            out.append(self._canonize_row(r.get("timestamp") or r.get("time"), r.get("open"), r.get("high"), r.get("low"), r.get("close"), r.get("volume")))
                    if out:
                        return out
                if hasattr(self.kite, "get_historical"):
                    raw = self.kite.get_historical(symbol, from_ts, to_ts, interval)
        except Exception:
            traceback.print_exc()

        # 2) yfinance fallback
        try:
            if yf is not None:
                sym = symbol if symbol.endswith(".NS") else (symbol + ".NS" if not symbol.upper().startswith("NIFTY") else symbol)
                yf_interval = interval
                start = from_ts
                end = to_ts
                period = None
                if not start and not end:
                    period = "7d"
                if period:
                    df = yf.download(sym, period=period, interval=yf_interval, progress=False, threads=False)
                else:
                    df = yf.download(sym, start=start, end=end, interval=yf_interval, progress=False, threads=False)
                if df is None or df.empty:
                    return []
                out = []
                for idx, row in df.iterrows():
                    ts = idx.to_pydatetime().isoformat()
                    out.append(self._canonize_row(ts, row['Open'], row['High'], row['Low'], row['Close'], int(row.get('Volume', 0))))
                return out
        except Exception:
            traceback.print_exc()

        return []
