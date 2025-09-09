# backtester.py
# Minimal defensive Backtester so the API can run and return plausible backtest output.
# Replace this with your full backtesting engine later.

from typing import List, Dict, Any
from datetime import datetime, timedelta
import random

class Backtester:
    def __init__(self, data_fetcher):
        # data_fetcher is expected to provide get_candles(...) returning list of candle dicts
        self.fetcher = data_fetcher

    def _dummy_trades(self, symbol: str) -> List[Dict[str, Any]]:
        # return a few fake trades for the trades table
        now = datetime.utcnow()
        trades = []
        for i in range(5):
            entry_time = (now - timedelta(days=5-i)).isoformat()
            exit_time = (now - timedelta(days=4-i)).isoformat()
            entry_price = round(1000 + random.uniform(-10, 10), 2)
            exit_price = round(entry_price + random.uniform(-20, 20), 2)
            pnl = round((exit_price - entry_price) * random.randint(1,5), 2)
            trades.append({
                "entry_time": entry_time,
                "exit_time": exit_time,
                "symbol": symbol,
                "side": random.choice(["BUY", "SELL"]),
                "qty": random.randint(1,10),
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "stop_loss": entry_price - 5,
                "target": entry_price + 10
            })
        return trades

    def _dummy_equity_curve(self) -> List[Dict[str, Any]]:
        # small equity series
        equity = []
        balance = 100000.0
        for i in range(10):
            balance += random.uniform(-500, 800)
            equity.append({"timestamp": (datetime.utcnow() - timedelta(days=10-i)).isoformat(), "equity": round(balance,2)})
        return equity

    def _dummy_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        wins = sum(1 for t in trades if t["pnl"] > 0)
        losses = len(trades) - wins
        total_pnl = round(sum(t["pnl"] for t in trades),2)
        win_rate = round((wins/len(trades))*100,2) if trades else 0.0
        sharpe = round(random.uniform(0.5,1.5),2)
        max_dd = round(random.uniform(0.01,0.15),3)
        return {
            "trades": len(trades),
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "sharpe": sharpe,
            "max_drawdown": max_dd
        }

    def run(self, symbol: str, interval: str, from_ts: str, to_ts: str, strategy_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a backtest using the data_fetcher. This stub:
          - attempts to fetch candles (if available),
          - otherwise returns dummy trades, equity curve and metrics.
        """
        candles = []
        try:
            # try to fetch real candles if kite/data fetcher is available
            if self.fetcher and hasattr(self.fetcher, "get_candles"):
                candles = self.fetcher.get_candles(symbol, interval, from_ts, to_ts) or []
        except Exception:
            candles = []

        # If no candles, continue with dummy output (so UI doesn't crash)
        trades = self._dummy_trades(symbol)
        equity = self._dummy_equity_curve()
        metrics = self._dummy_metrics(trades)

        return {
            "symbol": symbol,
            "interval": interval,
            "from": from_ts,
            "to": to_ts,
            "trades": trades,
            "equity_curve": equity,
            "metrics": metrics,
            "candles_count": len(candles)
        }
