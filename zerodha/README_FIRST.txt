Zerodha Trading App - Final Deliverable ZIP
-------------------------------------------
Contents:
- zerodha_trading_app_final4/ (full project: backend + frontend + tests)
- setup_guide/ (10 step PNG images)
- setup_guide.pdf (printable step guide)
- README_FIRST.txt (this file)

Quick start:
1. Unzip this package.
2. Follow setup_guide/step_*.png images or open setup_guide.pdf for step-by-step instructions.
3. Run backend: cd zerodha_trading_app_final4/backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && uvicorn main:app --reload --port 8000
4. Run frontend: cd zerodha_trading_app_final4/frontend && npm install && npm run dev
5. Use the UI to create strategy, run backtest, perform Zerodha Connect, and run live (PAPER_MODE first).

IMPORTANT: Keep KITE_ENC_KEY secure. Use PAPER_MODE=true for initial testing.
