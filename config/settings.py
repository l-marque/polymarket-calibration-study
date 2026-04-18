"""
Centralized configuration. All endpoints, rate limits, and tunables live here
so that changes to Polymarket's API don't require hunting through the codebase.
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


# --- Endpoints (verified from Polymarket docs as of 2026) ---
GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"
DATA_BASE = "https://data-api.polymarket.com"

GAMMA_MARKETS = f"{GAMMA_BASE}/markets"
GAMMA_EVENTS = f"{GAMMA_BASE}/events"
GAMMA_TAGS = f"{GAMMA_BASE}/tags"
CLOB_PRICES_HISTORY = f"{CLOB_BASE}/prices-history"


# --- Rate limits (token-bucket params, per Polymarket public docs) ---
# Global: 4000 / 10s. Per-endpoint stricter limits applied below.
@dataclass(frozen=True)
class RateBudget:
    name: str
    requests: int
    window_sec: float


GLOBAL_BUDGET = RateBudget("global", 4000, 10.0)
MARKETS_BUDGET = RateBudget("markets", 300, 10.0)
EVENTS_BUDGET = RateBudget("events", 500, 10.0)
CLOB_BUDGET = RateBudget("clob", 200, 10.0)  # conservative; CLOB doc-silent


# --- HTTP client tuning ---
HTTP_TIMEOUT_SEC = 30.0
HTTP_MAX_RETRIES = 5
HTTP_BACKOFF_BASE_SEC = 1.5  # exponential: 1.5, 2.25, 3.4, 5.1, 7.6


# --- Pagination ---
GAMMA_PAGE_SIZE = 500  # max accepted by /markets and /events


# --- Storage ---
DB_PATH = Path(os.getenv("DB_PATH", "./polymarket.db")).resolve()


# --- Holdout policy (anti-leakage) ---
# Markets resolved within this window are flagged holdout=True and excluded
# from any training/exploration until Phase 3 final validation.
HOLDOUT_DAYS = 30


# --- FRED macro series for geopolitical / macro context ---
# All public, daily where possible. Used in Phase 1 with strict ts <= ts join.
FRED_SERIES = {
    "VIXCLS":      "CBOE Volatility Index (risk appetite)",
    "DTWEXBGS":    "Trade-weighted USD index broad",
    "DCOILWTICO":  "Crude oil WTI spot price",
    "DGS10":       "10-year US Treasury yield",
    "DFF":         "Effective federal funds rate",
    "T10YIE":      "10y breakeven inflation expectation",
    "GPRD":        "Daily Geopolitical Risk Index (Caldara-Iacoviello)",
    "STLFSI4":     "St Louis Financial Stress Index",
}
FRED_API_KEY = os.getenv("FRED_API_KEY", "")


# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = Path("./logs/phase0.log").resolve()
