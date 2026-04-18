# Polymarket Calibration Study

> Empirical study of price calibration and market efficiency in decentralized prediction markets.

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-13%20passing-brightgreen.svg)](./tests)

## Abstract

This project investigates three pre-registered hypotheses about price inefficiencies in [Polymarket](https://polymarket.com), a decentralized prediction market on Polygon. The hypotheses are tested on a sample of 24,000+ resolved binary markets using rigorous statistical methodology designed to prevent the most common pitfalls of empirical finance: data snooping, look-ahead bias, and survivorship effects.

## Research Questions

1. **Favorite-longshot bias** — Do prices above 0.85 systematically over- or under-estimate the realized YES rate, after controlling for market category and liquidity?
2. **Late resolution drift** — Does the price trajectory in the 48 hours preceding market resolution carry information beyond the price level itself?
3. **Cross-market arbitrage** — Do logically related markets within the same Gamma event respect additive consistency, or do exploitable inconsistencies persist after transaction costs?

Each hypothesis is pre-registered in [`research_journal.md`](./research_journal.md) before any data analysis is performed, following Lakens' preregistration practices.

## Methodology

| Safeguard | Implementation |
|---|---|
| Temporal holdout | Markets resolved within 30 days flagged `holdout=1`, excluded from all exploratory analysis |
| As-of joins | External features (FRED macro series) joined under strict rule `feature_ts <= observation_ts` |
| Walk-forward validation | Six rolling windows (6-month train / 1-month test), no random K-fold |
| Multiple-testing correction | Bonferroni adjustment across decile-level tests |
| Rate-limit compliance | Token bucket respecting documented limits (4k/10s global, 300/10s on `/markets`) |
| Statistical robustness | Bootstrap confidence intervals (10,000 resamples), clustered standard errors by market |

Macroeconomic and geopolitical controls are introduced via FRED time series:
- **VIXCLS** — equity volatility (risk appetite)
- **GPRD** — Daily Geopolitical Risk Index (Caldara & Iacoviello, 2022)
- **DTWEXBGS** — broad trade-weighted USD
- **DGS10** — 10-year Treasury yield
- **DCOILWTICO** — WTI crude oil spot
- **DFF** — effective Fed funds rate
- **T10YIE** — 10y breakeven inflation
- **STLFSI4** — St. Louis Financial Stress Index

## Repository Structure

```
polymarket-calibration-study/
├── config/                # Endpoints, rate limits, tunables
├── data/
│   ├── collector.py       # Async Polymarket Gamma + CLOB ingestion
│   ├── storage.py         # SQLite schema with anti-leakage flags
│   ├── macro_collector.py # FRED macro/geopolitical controls
│   └── explorer.py        # Descriptive statistics and calibration probes
├── features/engineer.py   # Feature construction (Phase 1)
├── models/strategy.py     # Decision rules (Phase 1+)
├── backtest/engine.py     # Vectorbt walk-forward backtest (Phase 1+)
├── execution/bot.py       # Paper/live execution (Phase 3+)
├── tests/                 # Unit tests enforcing anti-leakage contracts
├── notebooks/             # Exploratory and confirmatory analysis
├── research_journal.md    # Weekly progress log + preregistered hypotheses
├── phase1_strategy_design.md  # Conditional strategy framework
└── run_phase0.py          # Entry point for data collection
```

## Project Phases

| Phase | Description | Status |
|---|---|---|
| **0** | Data collection (Polymarket + FRED) | In progress |
| **1** | Statistical analysis of pre-registered hypotheses | Next |
| **2** | Predictive modeling (logistic, XGBoost, Platt calibration) | Planned |
| **3** | Paper trading validation (30-day minimum) | Planned |
| **4** | Live execution with strict capital limits | Planned |

## Installation

```bash
git clone https://github.com/l-marque/polymarket-calibration-study.git
cd polymarket-calibration-study
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Get a free FRED API key at https://fred.stlouisfed.org/docs/api/api_key.html and paste it into `.env`.

## Usage

```bash
python run_phase0.py markets --months 12
python run_phase0.py prices --concurrency 4
python run_phase0.py macro --start 2020-01-01
python run_phase0.py explore

python -m pytest tests/ -v
```

## Current Dataset

As of April 18, 2026:
- 99,999 markets indexed from Gamma API
- 24,067 markets with volume > $10,000 selected for price collection
- 8 FRED series spanning 2020–2026 for macro/geopolitical controls

## Known Limitations

- The CLOB `/prices-history` endpoint returns empty arrays for closed markets when `fidelity < 720` minutes (see [py-clob-client #216](https://github.com/Polymarket/py-clob-client/issues/216)). Automatic fallback to 12h granularity implemented.
- Polymarket's `feeSchedule` structure changed on March 31, 2026, requiring per-market fee lookup rather than category-level defaults.
- Gamma's `volume` field shows evidence of bucketing (see `research_journal.md` for diagnostic).

## References

- Caldara, D. & Iacoviello, M. (2022). Measuring Geopolitical Risk. *American Economic Review*, 112(4), 1194–1225.
- Griffith, R. M. (1949). Odds Adjustment by American Horse-Race Bettors. *American Journal of Psychology*, 62, 290–294.
- Manski, C. F. (2006). Interpreting the Predictions of Prediction Markets. *Economics Letters*, 91(3), 425–429.
- Lakens, D. (2019). The Value of Preregistration for Psychological Science: A Conceptual Analysis. *Japanese Psychological Review*, 62(3).
- Polymarket Documentation: https://docs.polymarket.com

## License

MIT License — see [LICENSE](./LICENSE).

## Author

**Lucas Marque** — MSc Engineering Student, Centrale Méditerranée  
Specialization: Quantitative Finance & Data-Driven Modeling  
Contact: lucas.marque@icloud.com