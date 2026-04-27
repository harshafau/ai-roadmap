from __future__ import annotations

import pandas as pd


def swing_highs(highs: pd.Series, left: int = 2, right: int = 2) -> pd.Series:
    """Boolean Series; True at fractal swing highs.

    A bar at index i is a swing high iff highs[i] >= highs[i-left:i+right+1].max()
    and is strictly greater than its immediate neighbours.
    """
    if left < 1 or right < 1:
        raise ValueError("left and right must be >= 1")
    n = len(highs)
    out = pd.Series(False, index=highs.index)
    for i in range(left, n - right):
        window = highs.iloc[i - left : i + right + 1]
        center = highs.iloc[i]
        if center == window.max() and center > highs.iloc[i - 1] and center > highs.iloc[i + 1]:
            out.iloc[i] = True
    return out


def swing_lows(lows: pd.Series, left: int = 2, right: int = 2) -> pd.Series:
    if left < 1 or right < 1:
        raise ValueError("left and right must be >= 1")
    n = len(lows)
    out = pd.Series(False, index=lows.index)
    for i in range(left, n - right):
        window = lows.iloc[i - left : i + right + 1]
        center = lows.iloc[i]
        if center == window.min() and center < lows.iloc[i - 1] and center < lows.iloc[i + 1]:
            out.iloc[i] = True
    return out
