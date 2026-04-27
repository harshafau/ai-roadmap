from __future__ import annotations

import pandas as pd


def volume_delta(bars: pd.DataFrame) -> pd.Series:
    """Bar-level volume delta proxy.

    True order-flow CVD requires per-trade aggressor classification (bid-hit vs
    ask-lift), which Dhan retail API does NOT expose. This is a pragmatic proxy
    used widely in retail backtests:

        delta_t = sign(close_t - open_t) * volume_t

    Cumulative delta is then `volume_delta(...).cumsum()`. Treat the magnitude
    as suggestive, not an institutional-grade footprint signal.
    """
    sign = (bars["close"] - bars["open"]).apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (sign * bars["volume"]).rename("volume_delta")
