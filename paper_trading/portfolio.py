"""Gestion du portfolio virtuel : entrées, résolutions, P&L."""
import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import requests

from config import (
    INITIAL_CAPITAL_USDC, STAKE_PER_TRADE_USDC, FEE_ROUND_TRIP, SLIPPAGE,
    TRADES_CSV, PORTFOLIO_CSV, STATE_JSON, GAMMA_API_URL,
)

logger = logging.getLogger(__name__)

TRADES_FIELDS = [
    "trade_id", "market_id", "slug", "question",
    "entry_time", "entry_price_yes", "entry_price_no",
    "effective_cost_no", "shares_no", "stake_usdc",
    "expected_end_time", "status",
    "resolution_time", "outcome_yes", "gross_payout", "net_payout", "pnl",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_state() -> Dict:
    if STATE_JSON.exists():
        return json.loads(STATE_JSON.read_text())
    return {"capital": INITIAL_CAPITAL_USDC, "open_market_ids": []}


def _save_state(state: Dict):
    STATE_JSON.write_text(json.dumps(state, indent=2))


def _ensure_trades_csv():
    if not TRADES_CSV.exists():
        with TRADES_CSV.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=TRADES_FIELDS).writeheader()


def _ensure_portfolio_csv():
    if not PORTFOLIO_CSV.exists():
        with PORTFOLIO_CSV.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["timestamp", "capital_usdc", "open_positions", "cumulative_pnl"])


def _read_trades() -> List[Dict]:
    if not TRADES_CSV.exists():
        return []
    with TRADES_CSV.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_trades(trades: List[Dict]):
    with TRADES_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=TRADES_FIELDS)
        w.writeheader()
        w.writerows(trades)


def open_position(market: Dict) -> bool:
    """Enregistre une nouvelle position short-YES (achat NO). Retourne True si ouverte."""
    _ensure_trades_csv()
    state = _load_state()

    market_id = str(market["id"])
    if market_id in state["open_market_ids"]:
        return False

    # Parse prix YES
    import json as _json
    prices = market.get("outcomePrices")
    if isinstance(prices, str):
        prices = _json.loads(prices)
    yes_price = float(prices[0])
    no_price = 1.0 - yes_price

    # Coût effectif d'achat de NO (slippage + moitié des frais à l'entrée)
    effective_cost = no_price * (1 + SLIPPAGE) * (1 + FEE_ROUND_TRIP / 2)
    shares_no = STAKE_PER_TRADE_USDC / effective_cost

    trade = {
        "trade_id": f"trade_{market_id}_{int(datetime.now(timezone.utc).timestamp())}",
        "market_id": market_id,
        "slug": market.get("slug", ""),
        "question": market.get("question", "")[:200],
        "entry_time": _now_iso(),
        "entry_price_yes": round(yes_price, 4),
        "entry_price_no": round(no_price, 4),
        "effective_cost_no": round(effective_cost, 4),
        "shares_no": round(shares_no, 4),
        "stake_usdc": STAKE_PER_TRADE_USDC,
        "expected_end_time": market.get("endDate", ""),
        "status": "OPEN",
        "resolution_time": "",
        "outcome_yes": "",
        "gross_payout": "",
        "net_payout": "",
        "pnl": "",
    }

    trades = _read_trades()
    trades.append(trade)
    _write_trades(trades)

    state["open_market_ids"].append(market_id)
    _save_state(state)

    logger.info(f"OUVERTURE {market_id} | YES={yes_price:.3f} NO={no_price:.3f} shares={shares_no:.2f}")
    return True


def resolve_open_positions():
    """Vérifie si des positions ouvertes sont résolues et calcule leur P&L."""
    _ensure_trades_csv()
    _ensure_portfolio_csv()
    state = _load_state()

    trades = _read_trades()
    open_trades = [t for t in trades if t["status"] == "OPEN"]

    if not open_trades:
        return

    updated_count = 0
    for t in open_trades:
        market_id = t["market_id"]
        # Query Gamma pour voir si résolu
        try:
            r = requests.get(f"{GAMMA_API_URL}/{market_id}", timeout=30)
            if r.status_code != 200:
                continue
            data = r.json()
        except Exception as e:
            logger.warning(f"Erreur fetch résolution {market_id}: {e}")
            continue

        # Marché résolu ?
        closed = data.get("closed", False)
        if not closed:
            continue

        # Parse outcome
        import json as _json
        prices = data.get("outcomePrices")
        if isinstance(prices, str):
            prices = _json.loads(prices)
        if not prices:
            continue
        final_yes = float(prices[0])
        outcome_yes = final_yes > 0.5  # True si YES a gagné

        # On a acheté NO : on gagne si outcome = NO
        shares_no = float(t["shares_no"])
        if outcome_yes:
            gross = 0.0
        else:
            gross = shares_no * 1.0  # chaque share NO paie 1 USDC

        # Frais de sortie
        net_payout = gross * (1 - FEE_ROUND_TRIP / 2)
        pnl = net_payout - float(t["stake_usdc"])

        # Update
        t["status"] = "CLOSED"
        t["resolution_time"] = _now_iso()
        t["outcome_yes"] = str(outcome_yes)
        t["gross_payout"] = round(gross, 4)
        t["net_payout"] = round(net_payout, 4)
        t["pnl"] = round(pnl, 4)

        state["capital"] += pnl
        if market_id in state["open_market_ids"]:
            state["open_market_ids"].remove(market_id)

        updated_count += 1
        logger.info(f"FERMETURE {market_id} | outcome_YES={outcome_yes} | P&L={pnl:+.2f}")

    if updated_count > 0:
        _write_trades(trades)
        _save_state(state)
        # Log portfolio snapshot
        cumulative_pnl = sum(float(t["pnl"]) for t in trades if t["pnl"] != "")
        with PORTFOLIO_CSV.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                _now_iso(), round(state["capital"], 2),
                len(state["open_market_ids"]), round(cumulative_pnl, 2)
            ])


def print_summary():
    """Affiche un résumé de l'état du portfolio."""
    state = _load_state()
    trades = _read_trades()
    closed = [t for t in trades if t["status"] == "CLOSED"]
    open_trades = [t for t in trades if t["status"] == "OPEN"]

    print("\n" + "=" * 60)
    print("PAPER TRADING PORTFOLIO SUMMARY")
    print("=" * 60)
    print(f"Capital virtuel actuel : {state['capital']:.2f} USDC")
    print(f"Capital initial        : {INITIAL_CAPITAL_USDC:.2f} USDC")
    print(f"P&L total              : {state['capital'] - INITIAL_CAPITAL_USDC:+.2f} USDC")
    print(f"Positions ouvertes     : {len(open_trades)}")
    print(f"Trades clôturés        : {len(closed)}")
    if closed:
        wins = sum(1 for t in closed if float(t["pnl"]) > 0)
        print(f"Taux de gain           : {wins}/{len(closed)} ({100*wins/len(closed):.1f}%)")
        total_pnl = sum(float(t["pnl"]) for t in closed)
        total_stake = sum(float(t["stake_usdc"]) for t in closed)
        if total_stake > 0:
            print(f"ROI par trade          : {100*total_pnl/total_stake:+.2f}%")
    print("=" * 60 + "\n")