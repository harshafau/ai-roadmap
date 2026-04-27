from __future__ import annotations

import numpy as np
import pandas as pd


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI. Bounded [0, 100]. RSI=100 when no down moves, RSI=0 when no up moves."""
    if period <= 0:
        raise ValueError("period must be positive")
    delta = close.diff().fillna(0.0)
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()

    out = pd.Series(50.0, index=close.index, name=f"rsi_{period}")
    both_zero = (avg_gain == 0) & (avg_loss == 0)
    only_gain = (avg_loss == 0) & (avg_gain > 0)
    only_loss = (avg_gain == 0) & (avg_loss > 0)
    normal = ~(both_zero | only_gain | only_loss)

    rs = avg_gain[normal] / avg_loss[normal]
    out.loc[normal] = 100.0 - 100.0 / (1.0 + rs)
    out.loc[only_gain] = 100.0
    out.loc[only_loss] = 0.0
    return out
