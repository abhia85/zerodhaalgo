# data_fetcher.py
from typing import List, Dict, Optional
from datetime import datetime
from .logger import logger

try:
    import yfinance as yf
    HAVE_YFINANCE = True
except Exception:
    HAVE_YFINANCE = False

class DataFetcher:
    def __init__(self, kite_client=None):
        self.kite = kite_client

    def list_nse_symbols(self) -> List[str]:
        try:
            if self.kite:
                if hasattr(self.kite, 'get_instruments'):
                    ins = self.kite.get_instruments()
                    out = []
                    for i in ins:
                        if isinstance(i, dict):
                            sym = i.get('tradingsymbol') or i.get('symbol')
                            if sym: out.append(sym)
                    if out: return out
                if hasattr(self.kite, 'instruments') and isinstance(self.kite.instruments, list):
                    return [getattr(x, 'tradingsymbol', getattr(x, 'symbol', str(x))) for x in self.kite.instruments]
        except Exception as e:
            logger.warning('kite list_nse_symbols error: %s', e)
        return ['NIFTY 50', 'BANKNIFTY', 'RELIANCE.NS', 'TCS.NS', 'INFY.NS']

    def _to_candle(self, dt, o, h, l, c, v):
        return {
            'timestamp': dt.isoformat() if isinstance(dt, datetime) else str(dt),
            'open': float(o),
            'high': float(h),
            'low': float(l),
            'close': float(c),
            'volume': int(v or 0)
        }

    def _try_parse_raw_dict(self, raw):
        try:
            ts = raw.get('timestamp') or raw.get('time') or raw.get('date') or raw.get('datetime')
            if isinstance(ts, (int, float)):
                dt = datetime.utcfromtimestamp(ts/1000.0)
            else:
                dt = ts
            return self._to_candle(dt, raw.get('open', 0), raw.get('high', 0), raw.get('low', 0), raw.get('close', 0), raw.get('volume', 0))
        except Exception:
            return None

    def get_candles(self, symbol: str, interval: str = '5m', from_ts: Optional[str] = None, to_ts: Optional[str] = None) -> List[Dict]:
        try:
            if self.kite:
                if hasattr(self.kite, 'get_candles'):
                    raw = self.kite.get_candles(symbol, interval, from_ts, to_ts)
                    out = []
                    for r in raw:
                        try:
                            ts = r[0]
                            if isinstance(ts, (int, float)):
                                dt = datetime.utcfromtimestamp(ts/1000.0)
                            else:
                                dt = ts
                            out.append(self._to_candle(dt, r[1], r[2], r[3], r[4], r[5]))
                        except Exception:
                            continue
                    return out
                if hasattr(self.kite, 'get_historical'):
                    raw = self.kite.get_historical(symbol, from_ts, to_ts, interval)
                    out = []
                    for r in raw:
                        c = self._try_parse_raw_dict(r)
                        if c: out.append(c)
                    return out
        except Exception as e:
            logger.warning('kite data fetch error: %s', e)

        if HAVE_YFINANCE:
            try:
                if from_ts and to_ts:
                    df = yf.download(symbol, start=from_ts, end=to_ts, interval=interval)
                else:
                    df = yf.download(symbol, period='7d', interval=interval)
                out = []
                for idx, row in df.iterrows():
                    out.append(self._to_candle(idx.to_pydatetime(), row['Open'], row['High'], row['Low'], row['Close'], row.get('Volume', 0)))
                return out
            except Exception as e:
                logger.warning('yfinance fetch failed: %s', e)

        logger.info('No data source available for %s %s -> returning empty candles', symbol, interval)
        return []
