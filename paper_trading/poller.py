"""Interroge l'API Gamma pour récupérer les marchés actifs qui correspondent à la stratégie."""
import time
import logging
import requests
from datetime import datetime, timezone
from typing import List, Dict

from config import (
    GAMMA_API_URL, PRICE_MIN, PRICE_MAX, MIN_DURATION_DAYS, MIN_VOLUME_USD,
    EXCLUDE_PRICE_EXACT, T_MINUS_HOURS_MIN, T_MINUS_HOURS_MAX, ALLOWED_CATEGORIES,
)
from classifier import classify

logger = logging.getLogger(__name__)


def fetch_active_markets(limit: int = 500) -> List[Dict]:
    """Récupère les marchés actifs depuis Gamma."""
    params = {"active": "true", "closed": "false", "limit": limit}
    try:
        r = requests.get(GAMMA_API_URL, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"Erreur API Gamma: {e}")
        return []


def is_candidate(market: Dict) -> bool:
    """Vérifie si un marché satisfait tous les filtres de la stratégie."""
    try:
        # Catégorie
        cat = classify(market.get("slug", ""))
        if cat not in ALLOWED_CATEGORIES:
            return False

        # Prix YES actuel
        outcomes_prices = market.get("outcomePrices")
        if not outcomes_prices:
            return False
        if isinstance(outcomes_prices, str):
            import json as _json
            outcomes_prices = _json.loads(outcomes_prices)
        yes_price = float(outcomes_prices[0])

        if not (PRICE_MIN <= yes_price <= PRICE_MAX):
            return False
        if abs(yes_price - EXCLUDE_PRICE_EXACT) < 1e-6:
            return False

        # Volume
        vol = float(market.get("volume", 0))
        if vol < MIN_VOLUME_USD:
            return False

        # Durée totale
        start_date = market.get("startDate")
        end_date = market.get("endDate")
        if not start_date or not end_date:
            return False
        start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        duration_days = (end - start).total_seconds() / 86400
        if duration_days < MIN_DURATION_DAYS:
            return False

        # On entre à T-24h (entre T-20h et T-28h pour tolérance du polling horaire)
        now = datetime.now(timezone.utc)
        hours_to_resolution = (end - now).total_seconds() / 3600
        if not (T_MINUS_HOURS_MIN <= hours_to_resolution <= T_MINUS_HOURS_MAX):
            return False

        return True
    except Exception as e:
        logger.warning(f"Erreur filtrage marché {market.get('id')}: {e}")
        return False


def find_candidates() -> List[Dict]:
    """Retourne la liste des marchés candidats à l'entrée."""
    markets = fetch_active_markets()
    candidates = [m for m in markets if is_candidate(m)]
    logger.info(f"Poll: {len(markets)} marchés actifs, {len(candidates)} candidats")
    return candidates