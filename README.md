# Polymarket Calibration Study

> Empirical study of price calibration and market efficiency in decentralized prediction markets.

## Abstract

This project investigates three pre-registered hypotheses about price
inefficiencies in Polymarket, a decentralized prediction market on Polygon:

1. **Favorite-longshot bias**: systematic miscalibration at the extremes of the
   probability distribution (prices above 0.85 and below 0.15).
2. **Late resolution drift**: directional price drift in the 48 hours preceding
   market resolution beyond what new information flow would justify.
3. **Cross-market arbitrage**: logical inconsistencies between semantically
   related markets within the same event.

Hypotheses are tested using Brier score decomposition, chi-squared independence
tests, and walk-forward validation with Bonferroni correction for multiple
comparisons. Geopolitical and macroeconomic controls are introduced via FRED
time series (VIX, GPRD, DTWEXBGS, DGS10) under a strict as-of join discipline
to prevent look-ahead bias.

## Repository Structure


polymarket-calibration-study/
├── config/              # Endpoints, rate limits, tunables
├── data/
│   ├── collector.py     # Async Polymarket Gamma + CLOB ingestion
│   ├── storage.py       # SQLite schema with anti-leakage flags
│   ├── macro_collector.py  # FRED macro/geopolitical controls
│   └── explorer.py      # Descriptive statistics and calibration probes
├── features/engineer.py # Feature construction (Phase 1)
├── models/strategy.py   # Decision rules (Phase 1+)
├── backtest/engine.py   # Vectorbt walk-forward backtest (Phase 1+)
├── execution/bot.py     # Paper/live execution (Phase 3+)
├── tests/               # Unit tests enforcing anti-leakage contracts
├── notebooks/           # Exploratory and confirmatory analysis
└── run_phase0.py        # Entry point for data collection


## Methodological Safeguards

- **Temporal holdout**: markets resolved within the last 30 days are flagged
  `holdout=1` and excluded from any exploratory or training query until final
  validation.
- **As-of joins**: all external features (macroeconomic series, inter-market
  relationships) are joined to market observations under the rule
  `feature_ts <= market_observation_ts`.
- **Walk-forward validation**: six rolling windows (6-month train, 1-month
  test) rather than random cross-validation, to preserve temporal ordering.
- **Multiple-testing correction**: Bonferroni adjustment applied across all
  decile-level hypothesis tests.
- **Rate-limit compliance**: token-bucket implementation respecting published
  limits (4000/10s global, 300/10s on /markets, 500/10s on /events).

## Status

Phase 0 (data collection and exploration) is in progress. See
`research_journal.md` for weekly progress updates.

## Installation

```bash
git clone https://github.com/l-marque/polymarket-calibration-study.git
cd polymarket-calibration-study
py -3.12 -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # Edit to add your free FRED API key
python run_phase0.py markets --months 12
```

## References

- Caldara, D. & Iacoviello, M. (2022). "Measuring Geopolitical Risk."
  *American Economic Review*, 112(4).
- Griffith, R. M. (1949). "Odds Adjustment by American Horse-Race Bettors."
  *American Journal of Psychology*, 62.
- Manski, C. F. (2006). "Interpreting the Predictions of Prediction Markets."
  *Economics Letters*, 91(3).
- Polymarket Documentation: https://docs.polymarket.com

## License

MIT License — see LICENSE file.

## Author

**Lucas Marque** — MSc Engineering, Centrale Méditerranée  
Contact: lucas.marque@centrale-marseille.fr