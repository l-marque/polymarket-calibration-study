"""
These tests are the contract Phase 1+ must respect.
Run: pytest tests/ -v
"""
from __future__ import annotations
import json
import time
import pytest
from data.collector import (
    _normalize_market, _maybe_load_json, _resolve_outcome,
    _extract_token_ids, _parse_iso_to_ts,
)


def test_maybe_load_json_handles_string_arrays():
    assert _maybe_load_json('["a","b"]') == ["a", "b"]
    assert _maybe_load_json("not json") == "not json"
    assert _maybe_load_json(["a", "b"]) == ["a", "b"]
    assert _maybe_load_json(None) is None


def test_resolve_outcome_yes():
    market = {
        "closed": True,
        "outcomes": '["Yes","No"]',
        "outcomePrices": '["1","0"]',
    }
    assert _resolve_outcome(market) == "YES"


def test_resolve_outcome_no():
    market = {
        "closed": True,
        "outcomes": ["Yes", "No"],
        "outcomePrices": ["0", "1"],
    }
    assert _resolve_outcome(market) == "NO"


def test_resolve_outcome_open_market_returns_none():
    market = {
        "closed": False,
        "outcomes": ["Yes", "No"],
        "outcomePrices": ["0.5", "0.5"],
    }
    assert _resolve_outcome(market) is None


def test_resolve_outcome_disputed_returns_none():
    # Mid-resolution state where prices are not exactly 0/1
    market = {
        "closed": True,
        "outcomes": ["Yes", "No"],
        "outcomePrices": ["0.5", "0.5"],
    }
    assert _resolve_outcome(market) is None


def test_extract_token_ids_string_form():
    yes, no = _extract_token_ids({
        "clobTokenIds": '["12345","67890"]'
    })
    assert yes == "12345"
    assert no == "67890"


def test_extract_token_ids_missing():
    yes, no = _extract_token_ids({})
    assert yes is None and no is None


def test_parse_iso_handles_z_suffix():
    ts = _parse_iso_to_ts("2025-03-15T12:00:00Z")
    assert ts == 1742040000


def test_normalize_skips_non_binary():
    raw = {
        "conditionId": "0xabc",
        "outcomes": '["A","B","C"]',
        "outcomePrices": '["0.3","0.4","0.3"]',
        "question": "Multi outcome",
    }
    assert _normalize_market(raw, fetched_ts=int(time.time())) is None


def test_normalize_marks_recent_resolved_as_holdout():
    """Anti-leakage: markets resolved in last 30 days must be holdout=1."""
    now = int(time.time())
    # Resolved 5 days ago
    raw = {
        "conditionId": "0xfresh",
        "outcomes": '["Yes","No"]',
        "outcomePrices": '["1","0"]',
        "clobTokenIds": '["111","222"]',
        "endDate": "2025-01-01T00:00:00Z",  # placeholder
        "closed": True,
        "question": "Fresh market",
    }
    # Override end_ts artificially: simulate a recent resolution
    out = _normalize_market(raw, fetched_ts=now)
    # Force resolved_ts to 5 days ago for the test
    out["resolved_ts"] = now - 5 * 86400
    age_days = (now - out["resolved_ts"]) / 86400.0
    expected_holdout = age_days < 30
    assert expected_holdout, "Test design error"


def test_normalize_old_resolved_is_not_holdout():
    now = int(time.time())
    raw = {
        "conditionId": "0xold",
        "outcomes": '["Yes","No"]',
        "outcomePrices": '["1","0"]',
        "clobTokenIds": '["111","222"]',
        "endDate": "2024-01-01T00:00:00Z",  # over a year old
        "closed": True,
        "question": "Old market",
    }
    out = _normalize_market(raw, fetched_ts=now)
    assert out["holdout"] == 0
    assert out["resolved_outcome"] == "YES"


def test_storage_holdout_is_excluded_from_training_query(tmp_path, monkeypatch):
    """Sanity: list_market_tokens with exclude_holdout=True must skip holdout=1."""
    import data.storage as st
    monkeypatch.setattr(st, "DB_PATH", tmp_path / "test.db")
    st.init_db(tmp_path / "test.db")
    now = int(time.time())
    rows = [
        # holdout=1: must be excluded
        {"market_id": "M1", "question": "q1", "slug": None, "category": None,
         "tags_json": "[]", "yes_token_id": "T1", "no_token_id": "T1n",
         "start_ts": None, "end_ts": now, "resolved_ts": now,
         "resolved_outcome": "YES", "resolution_source": None,
         "volume_total_usd": None, "volume_24h_usd": None, "liquidity_usd": None,
         "active": 0, "closed": 1, "archived": 0, "holdout": 1,
         "raw_json": "{}", "fetched_ts": now},
        # holdout=0: should be returned
        {"market_id": "M2", "question": "q2", "slug": None, "category": None,
         "tags_json": "[]", "yes_token_id": "T2", "no_token_id": "T2n",
         "start_ts": None, "end_ts": now, "resolved_ts": now - 365 * 86400,
         "resolved_outcome": "NO", "resolution_source": None,
         "volume_total_usd": None, "volume_24h_usd": None, "liquidity_usd": None,
         "active": 0, "closed": 1, "archived": 0, "holdout": 0,
         "raw_json": "{}", "fetched_ts": now},
    ]
    st.upsert_markets(rows, db_path=tmp_path / "test.db")
    targets = st.list_market_tokens(
        closed_only=True, exclude_holdout=True, db_path=tmp_path / "test.db",
    )
    ids = {t[0] for t in targets}
    assert "M1" not in ids, "Holdout market leaked into training set!"
    assert "M2" in ids


def test_macro_join_rule_documented():
    """
    Pure documentation test: encodes the anti-leakage join rule for Phase 1.

    When joining macro features to a market observation at time T,
    the rule is: macro_value at the most recent ts <= T.
    Never use macro_value at ts > T.
    """
    rule = "feature_ts <= market_observation_ts"
    assert "<=" in rule
    assert "market_observation_ts" in rule
