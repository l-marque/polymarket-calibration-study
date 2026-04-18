"""
Phase 1+: trading strategy / decision rules.

Will be implemented after Phase 0 calibration probe identifies the actual
biases. Expected interface:

    @dataclass
    class Signal:
        market_id: str
        side: Literal["YES","NO","NONE"]
        edge_estimate: float        # in price units (e.g. 0.07 = 7c)
        confidence: float           # in [0, 1]
        size_fraction: float        # Kelly fraction in [0, 1]

    def decide(features: dict) -> Signal: ...
"""
