"""Configuration du bot paper trading."""
from pathlib import Path

# Capital virtuel initial
INITIAL_CAPITAL_USDC = 1000.0
STAKE_PER_TRADE_USDC = 10.0  # 1% du capital par trade

# Filtres de la stratégie (identiques au notebook 05)
PRICE_MIN = 0.50
PRICE_MAX = 0.60
MIN_DURATION_DAYS = 2
MIN_VOLUME_USD = 1000.0
EXCLUDE_PRICE_EXACT = 0.50

# Coûts de transaction
FEE_ROUND_TRIP = 0.02  # 2% aller-retour
SLIPPAGE = 0.005  # 0.5% entrée

# Timing
POLL_INTERVAL_SECONDS = 3600  # 1h entre chaque check
T_MINUS_HOURS_MIN = 20  # on entre entre T-20h et T-28h
T_MINUS_HOURS_MAX = 28

# Catégories acceptées
ALLOWED_CATEGORIES = {"crypto"}

# APIs Polymarket
GAMMA_API_URL = "https://gamma-api.polymarket.com/markets"
CLOB_API_URL = "https://clob.polymarket.com"

# Paths
BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
TRADES_CSV = LOG_DIR / "trades.csv"
PORTFOLIO_CSV = LOG_DIR / "portfolio.csv"
STATE_JSON = LOG_DIR / "state.json"