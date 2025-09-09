# backtester.py - minimal SMA crossover demo backtester
from typing import Dict, List
import pandas as pd
import numpy as np
import io, csv, base64
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime

class Backtester:
    def __init__(self, fetcher):
        self.fetcher = fetcher

    def _candles_to_df(self, candles):
        if not candles:
            return pd.DataFrame()
        df = pd.DataFrame(candles)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp").sort_index()
        return df

    def run(self, symbol: str, interval: str, from_ts: str, to_ts: str, strategy_payload: dict) -> Dict:
        raw = self.fetcher.get_candles(symbol, interval, from_ts, to_ts)
        df = self._candles_to_df(raw)
        if df.empty:
            return {"error": "no_data", "candles_count": 0, "trades": [], "equity": [], "metrics": {}}

        params = strategy_payload.get("params", {"fast":10, "slow":30, "risk_per_trade_pct":1.0})
        fast = int(params.get("fast",10))
        slow = int(params.get("slow",30))
        df["s_fast"] = df["close"].rolling(fast).mean()
        df["s_slow"] = df["close"].rolling(slow).mean()
        df = df.dropna()

        position = 0
        entry_price = 0.0
        trades = []
        cash = 100000.0
        position_size = 0
        nav_list = []

        for idx, row in df.iterrows():
            if row["s_fast"] > row["s_slow"] and position == 0:
                position = 1
                entry_price = row["close"]
                allocation = strategy_payload.get("allocation", 1.0)
                capital_to_use = cash * allocation
                qty = int(capital_to_use // entry_price)
                if qty <= 0:
                    continue
                position_size = qty
                cash -= qty * entry_price
                trades.append({"entry_ts": idx.isoformat(), "entry_price": float(entry_price), "qty": qty, "side": "BUY", "exit_ts": None, "exit_price": None, "pnl": None})
            elif row["s_fast"] < row["s_slow"] and position == 1:
                exit_price = row["close"]
                qty = position_size
                cash += qty * exit_price
                pnl = (exit_price - entry_price) * qty
                t = trades[-1]
                t["exit_ts"] = idx.isoformat()
                t["exit_price"] = float(exit_price)
                t["pnl"] = float(pnl)
                position = 0
                position_size = 0
                entry_price = 0.0

            market_val = (position_size * row["close"]) if position_size else 0.0
            nav = cash + market_val
            nav_list.append({"ts": idx.isoformat(), "equity": float(nav)})

        # close any open position at the end
        if position == 1 and position_size > 0:
            last_price = df.iloc[-1]["close"]
            cash += position_size * last_price
            pnl = (last_price - entry_price) * position_size
            t = trades[-1]
            t["exit_ts"] = df.index[-1].isoformat()
            t["exit_price"] = float(last_price)
            t["pnl"] = float(pnl)

        pnls = [t["pnl"] for t in trades if t.get("pnl") is not None]
        wins = [p for p in pnls if p > 0]
        win_rate = (len(wins) / len(pnls)) if pnls else 0.0
        cumrets = pd.Series([e["equity"] for e in nav_list])
        returns = cumrets.pct_change().dropna()
        sharpe = (returns.mean() / returns.std() * (252 ** 0.5)) if not returns.empty and returns.std() != 0 else 0.0
        series = np.array([e["equity"] for e in nav_list])
        mdd = 0.0
        if series.size:
            running_max = np.maximum.accumulate(series)
            drawdowns = (series - running_max) / running_max
            mdd = float(np.min(drawdowns)) if drawdowns.size else 0.0

        metrics = {"trades": len(pnls), "win_rate": float(win_rate), "sharpe": float(sharpe), "max_drawdown": float(mdd)}

        # CSV generation
        csv_buf = io.StringIO()
        w = csv.writer(csv_buf)
        w.writerow(["entry_ts","exit_ts","side","qty","entry_price","exit_price","pnl"])
        for t in trades:
            w.writerow([t.get("entry_ts"), t.get("exit_ts"), t.get("side"), t.get("qty"), t.get("entry_price"), t.get("exit_price"), t.get("pnl")])
        csv_b64 = base64.b64encode(csv_buf.getvalue().encode()).decode()

        # equity PNG (base64)
        img_buf = io.BytesIO()
        if nav_list:
            times = [pd.to_datetime(e["ts"]) for e in nav_list]
            eq = [e["equity"] for e in nav_list]
            plt.figure(figsize=(8,3))
            plt.plot(times, eq)
            plt.title("Equity Curve")
            plt.tight_layout()
            plt.savefig(img_buf, format="png", bbox_inches="tight")
            plt.close()
            img_buf.seek(0)
            png_b64 = base64.b64encode(img_buf.read()).decode()
        else:
            png_b64 = ""

        return {"trades": trades, "equity": nav_list, "metrics": metrics, "candles_count": len(df), "csv_b64": csv_b64, "png_b64": png_b64}
