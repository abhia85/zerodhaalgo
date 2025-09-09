
# Streaming worker: connects to Kite Connect WebSocket if KITE_STREAM_URL and access token present.
# Otherwise falls back to simulated low-latency polling.
import threading, time, os, json
from app.data_fetcher import DataFetcher

try:
    import websocket
except Exception:
    websocket = None

class StreamingWorker(threading.Thread):
    def __init__(self, kite_client, cfg):
        super().__init__(daemon=True)
        self.kite = kite_client
        self.cfg = cfg
        self._stop = threading.Event()
        self.fetcher = DataFetcher(kite_client)
        self.stream_url = os.getenv('KITE_STREAM_URL')  # e.g., 'wss://ws.kite.trade?api_key=...&access_token=...'

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            # handle ticks: frontend or evaluation logic can be added here
            print('tick', data)
        except Exception as e:
            print('ws message parse error', e)

    def _on_error(self, ws, error):
        print('ws error', error)

    def _on_close(self, ws, close_status_code, close_msg):
        print('ws closed', close_status_code, close_msg)

    def _on_open(self, ws):
        print('ws opened')

    def run(self):
        # If streaming URL present and websocket library available, attempt real streaming
        if self.stream_url and websocket:
            try:
                print('Attempting websocket connection to', self.stream_url)
                ws = websocket.WebSocketApp(self.stream_url,
                                            on_open=self._on_open,
                                            on_message=self._on_message,
                                            on_error=self._on_error,
                                            on_close=self._on_close)
                # run_forever is blocking; run in this thread
                ws.run_forever()
                return
            except Exception as e:
                print('websocket connection failed, falling back to polling:', e)

        # Fallback simulation: poll latest candle every second for quick response.
        symbol = getattr(self.cfg, 'symbol', os.getenv('DEFAULT_SYMBOL','RELIANCE.NS'))
        interval = getattr(self.cfg, 'interval', '1m')
        print('StreamingWorker (fallback) started for', symbol, 'interval', interval)
        while not self._stop.is_set():
            candles = self.fetcher.get_candles(symbol, interval, None, None)
            if candles:
                tick = candles[-1]
                # Ideally evaluate strategy on tick; here we print tick info
                print('simulated tick', tick.get('Datetime') or tick.get('Date') or tick.get('date') or tick)
            time.sleep(1)

    def stop(self):
        self._stop.set()
