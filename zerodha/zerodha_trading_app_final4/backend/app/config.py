# config.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))

PAPER_MODE = os.getenv("PAPER_MODE", "true").lower() in ("1","true","yes")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

KITE_API_KEY = os.getenv("KITE_API_KEY", "")
KITE_API_SECRET = os.getenv("KITE_API_SECRET", "")
KITE_ENC_KEY = os.getenv("KITE_ENC_KEY", "")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev_db.sqlite3")

DEFAULT_MAX_DAILY_LOSS = float(os.getenv("DEFAULT_MAX_DAILY_LOSS", "5000.0"))
DEFAULT_ALLOCATION = float(os.getenv("DEFAULT_ALLOCATION", "1.0"))

MAX_ORDERS_PER_MINUTE = int(os.getenv("MAX_ORDERS_PER_MINUTE", "5"))
