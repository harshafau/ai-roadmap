from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd


@dataclass(frozen=True)
class FairValueGap:
    direction: Literal["bullish", "bearish"]
    top: float          # upper edge of the gap
    bottom: float       # lower edge of the gap
    created_at: pd.Timestamp
    filled: bool = False


def detect_fair_value_gaps(bars: pd.DataFrame, lookback: int = 50) -> list[FairValueGap]:
    """Detect three-bar fair value gaps in the recent window.

    Bullish FVG: bar1.high < bar3.low (gap UP between bars 1 and 3, formed at bar 2).
      The gap region is [bar1.high, bar3.low]. Treated as a demand zone — price
      retests it for long entries.

    Bearish FVG: bar1.low > bar3.high (gap DOWN). Region [bar3.high, bar1.low].

    A gap is `filled` if any subsequent bar trades through its mid. We mark
    filled gaps and return all (caller can filter).
    """
    if len(bars) < 3:
        return []

    window = bars.iloc[-min(lookback, len(bars)) :]
    highs = window["high"].to_numpy()
    lows = window["low"].to_numpy()
    idx = window.index

    out: list[FairValueGap] = []
    for i in range(2, len(window)):
        b1_high, b1_low = highs[i - 2], lows[i - 2]
        b3_high, b3_low = highs[i], lows[i]

        if b1_high < b3_low:
            top, bottom = b3_low, b1_high
            direction: Literal["bullish", "bearish"] = "bullish"
        elif b1_low > b3_high:
            top, bottom = b1_low, b3_high
            direction = "bearish"
        else:
            continue

        mid = (top + bottom) / 2.0
        # Filled if any later bar's range contains the mid.
        filled = False
        if i + 1 < len(window):
            later = window.iloc[i + 1 :]
            filled = bool(((later["low"] <= mid) & (later["high"] >= mid)).any())

        out.append(
            FairValueGap(
                direction=direction,
                top=float(top),
                bottom=float(bottom),
                created_at=idx[i],
                filled=filled,
            )
        )
    return out


def latest_unfilled_fvg(
    bars: pd.DataFrame, direction: Literal["bullish", "bearish"], lookback: int = 50
) -> FairValueGap | None:
    candidates = [g for g in detect_fair_value_gaps(bars, lookback) if not g.filled and g.direction == direction]
    return candidates[-1] if candidates else None
