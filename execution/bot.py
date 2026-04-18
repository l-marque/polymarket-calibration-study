"""
Phase 3+: paper trading then live execution.

Hard rules:
- Phase 3: paper for 30 days. Pass criterion: realized Sharpe > 1.5,
  max drawdown < 20%, ≥ 50 trades.
- Phase 4: live with hard cap (initial 100-200 USDC). Circuit breakers:
    * stop new orders if daily loss > 5% of bankroll
    * stop new orders if 3 consecutive losing trades
    * stop everything if API errors > 5/min for 10 min
- Position sizing: half-Kelly, floor at 0.5 USDC, ceiling at 5% of bankroll.
- Order type: GTC limit at our price, never market orders (slippage).
"""
