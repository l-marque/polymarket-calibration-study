"""
Phase 1+: rigorous backtest with vectorbt.

Plan:
- Walk-forward time split (train rolling 6m, test next 1m, repeat).
- Trade simulation: assume taker fees of 2% (Polymarket standard for resolution),
  no maker rewards in our PnL until proven.
- Metrics: Sharpe, Sortino, max drawdown, hit rate, expectancy per trade,
  Brier score on out-of-sample probabilities.
- Holdout: never touch markets with holdout=1 until Phase 3 final validation.
"""
