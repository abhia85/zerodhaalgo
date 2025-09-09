# execution_manager.py
import time
import threading
from collections import deque
from typing import Dict, Any
from .logger import logger
from .config import PAPER_MODE, DEFAULT_MAX_DAILY_LOSS, DEFAULT_ALLOCATION, MAX_ORDERS_PER_MINUTE

class ExecutionManager:
    def __init__(self, kite_client, session_factory, models_db):
        self.kite = kite_client
        self.session_factory = session_factory
        self.models_db = models_db
        self.lock = threading.Lock()
        self.running = False
        self.order_timestamps = deque()

    def _can_send_order(self):
        now = time.time()
        while self.order_timestamps and now - self.order_timestamps[0] > 60:
            self.order_timestamps.popleft()
        return len(self.order_timestamps) < MAX_ORDERS_PER_MINUTE

    def _record_order(self):
        self.order_timestamps.append(time.time())

    def start_live(self, run_params: Dict[str,Any]):
        with self.lock:
            if self.running:
                return False, "already_running"
            self.running = True
            self._stop_event = threading.Event()
            self.max_daily_loss = run_params.get('max_daily_loss', DEFAULT_MAX_DAILY_LOSS)
            self.allocation = run_params.get('allocation', DEFAULT_ALLOCATION)
            self.capital = run_params.get('capital', 100000.0)
            self.worker = threading.Thread(target=self._run_loop, args=(run_params,), daemon=True)
            self.worker.start()
            logger.info('ExecutionManager: started live run: %s', run_params)
            return True, 'started'

    def stop_live(self):
        with self.lock:
            if not self.running:
                return False, 'not_running'
            self._stop_event.set()
            self.worker.join(timeout=5)
            self.running = False
            logger.info('ExecutionManager: stopped')
            return True, 'stopped'

    def _execute_order(self, order_payload):
        if PAPER_MODE:
            logger.info('PAPER_MODE: simulated order: %s', order_payload)
            try:
                if hasattr(self.models_db, 'record_trade_simulation'):
                    self.models_db.record_trade_simulation(order_payload)
            except Exception as e:
                logger.exception('failed to record simulated order: %s', e)
            return {'ok': True, 'simulated': True}
        if not self._can_send_order():
            logger.warning('Rate limit reached, order rejected')
            return {'ok': False, 'error': 'rate_limited'}
        if not self.kite.is_authenticated():
            return {'ok': False, 'error': 'kite_not_authenticated'}
        try:
            res = self.kite.place_order(order_payload)
            self._record_order()
            if hasattr(self.models_db, 'record_trade_live'):
                self.models_db.record_trade_live(order_payload, res)
            return {'ok': True, 'result': res}
        except Exception as e:
            logger.exception('Order placement failed: %s', e)
            return {'ok': False, 'error': str(e)}

    def _run_loop(self, run_params):
        daily_loss = 0.0
        while not self._stop_event.is_set():
            try:
                if daily_loss <= -abs(self.max_daily_loss):
                    logger.error('Max daily loss hit: %s. Stopping live run.', self.max_daily_loss)
                    self.stop_live()
                    return
                time.sleep(1)
            except Exception as e:
                logger.exception('Execution loop error: %s', e)
                time.sleep(1)
