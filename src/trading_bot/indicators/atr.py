from __future__ import annotations

import pandas as pd


def atr(bars: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range (Wilder)."""
    high = bars["high"]
    low = bars["low"]
    prev_close = bars["close"].shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean().rename(f"atr_{period}")
