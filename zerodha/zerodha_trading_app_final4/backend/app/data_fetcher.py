# data_fetcher.py
# Minimal robust DataFetcher wrapper so rom app.data_fetcher import DataFetcher works in the container.
# This file is intentionally defensive: it tries to use methods exposed by your KiteClient if present,
# and falls back to safe defaults (empty lists) so the server doesn't crash while we iterate.

from typing import List, Dict, Optional
from datetime import datetime

class DataFetcher:
    """
    Wrapper around a KiteClient-like object to provide:
      - get_candles(symbol, interval, from_ts, to_ts) -> list of candle dicts
      - list_nse_symbols() -> list of symbol strings
    This implementation tries common method names on the provided kite client and
    falls back to empty data if not available.
    """

    def __init__(self, kite_client):
        self.kite = kite_client

    def list_nse_symbols(self) -> List[str]:
        # Try possible methods on the kite client to return instruments/symbols
        try:
            if hasattr(self.kite, "get_instruments"):
                instruments = self.kite.get_instruments()
                # instruments may be list of dicts with 'tradingsymbol' or 'symbol'
                out = []
                for i in instruments:
                    if isinstance(i, dict):
                        if "tradingsymbol" in i:
                            out.append(i["tradingsymbol"])
                        elif "symbol" in i:
                            out.append(i["symbol"])
                if out:
                    return out
            # fallback: try attribute 'instruments' or 'symbols'
            if hasattr(self.kite, "instruments") and isinstance(self.kite.instruments, list):
                return [getattr(x, "tradingsymbol", getattr(x, "symbol", str(x))) for x in self.kite.instruments]
        except Exception:
            # defensive: don't crash the server on errors from kite client
            pass

        # Minimal safe fallback — helpful for UI to render dropdowns during testing.
        return ["NIFTY 50", "BANKNIFTY", "RELIANCE.NS", "TCS.NS", "INFY.NS"]

    def _parse_candle(self, raw) -> Optional[Dict]:
        """
        Accept a raw candle payload and convert to a canonical dict:
        { "timestamp": <iso>, "open": float, "high": float, "low": float, "close": float, "volume": int }
        """
        try:
            # Common Kite-like format: [timestamp_ms, open, high, low, close, volume]
            if isinstance(raw, (list, tuple)) and len(raw) >= 6:
                ts = raw[0]
                # Kite sometimes returns timestamp as ms int or as string ISO
                if isinstance(ts, (int, float)):
                    # assume ms
                    ts_iso = datetime.utcfromtimestamp(ts/1000.0).isoformat()
                else:
                    ts_iso = str(ts)
                return {
                    "timestamp": ts_iso,
                    "open": float(raw[1]),
                    "high": float(raw[2]),
                    "low": float(raw[3]),
                    "close": float(raw[4]),
                    "volume": int(raw[5])
                }
            # Common dict format
            if isinstance(raw, dict):
                # try many common keys
                ts = raw.get("timestamp") or raw.get("time") or raw.get("date") or raw.get("datetime")
                if isinstance(ts, (int, float)):
                    ts_iso = datetime.utcfromtimestamp(ts/1000.0).isoformat()
                else:
                    ts_iso = str(ts) if ts is not None else ""
                return {
                    "timestamp": ts_iso,
                    "open": float(raw.get("open", raw.get("o", 0))),
                    "high": float(raw.get("high", raw.get("h", 0))),
                    "low": float(raw.get("low", raw.get("l", 0))),
                    "close": float(raw.get("close", raw.get("c", 0))),
                    "volume": int(raw.get("volume", raw.get("v", 0)))
                }
        except Exception:
            return None

        return None

    def get_candles(self, symbol: str, interval: str = "5m", from_ts: Optional[str] = None, to_ts: Optional[str] = None) -> List[Dict]:
        """
        Return a list of canonical candle dicts.
        Attempts to call kite client using a few common method names:
          - get_candles(symbol, interval, from_ts, to_ts)
          - get_historical(symbol, from_ts, to_ts, interval)
          - get_ohlc or get_klines
        If none exist or an error occurs, returns an empty list.
        """
        try:
            # several possible kite client method names — try them in order
            if hasattr(self.kite, "get_candles"):
                raw = self.kite.get_candles(symbol, interval, from_ts, to_ts)
            elif hasattr(self.kite, "get_historical"):
                raw = self.kite.get_historical(symbol, from_ts, to_ts, interval)
            elif hasattr(self.kite, "get_ohlc"):
                raw = self.kite.get_ohlc(symbol, interval, from_ts, to_ts)
            elif hasattr(self.kite, "get_klines"):
                raw = self.kite.get_klines(symbol, interval, from_ts, to_ts)
            else:
                raw = None

            if raw is None:
                return []

            candles = []
            # raw could be a list of lists or list of dicts
            for r in raw:
                item = self._parse_candle(r)
                if item:
                    candles.append(item)
            return candles
        except Exception:
            # don't raise — return empty list so the server stays up
            return []
