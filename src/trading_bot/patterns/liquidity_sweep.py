from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from ..indicators.swing import swing_highs, swing_lows


@dataclass(frozen=True)
class LiquiditySweep:
    direction: Literal["bullish", "bearish"]
    swept_level: float    # the swing high/low that was taken out
    sweep_extreme: float  # the wick extreme of the sweep bar
    bar_index: pd.Timestamp


def detect_liquidity_sweep(
    bars: pd.DataFrame,
    lookback: int = 20,
    swing_left: int = 2,
    swing_right: int = 2,
) -> LiquiditySweep | None:
    """Detect a liquidity sweep on the LATEST closed bar.

    Bullish sweep (we expect upside reversion → BUY):
      - latest bar's low pierces the most recent swing low within `lookback`
      - latest bar closes back ABOVE that swing low (rejection)

    Bearish sweep (we expect downside reversion → SELL):
      - latest bar's high pierces the most recent swing high within `lookback`
      - latest bar closes back BELOW that swing high (rejection)

    Returns None if no sweep on the latest bar.
    """
    if len(bars) < max(lookback, swing_left + swing_right + 2):
        return None

    window = bars.iloc[-(lookback + 1) : -1]  # exclude latest bar from swing search
    latest = bars.iloc[-1]

    # Most recent confirmed swing high / low in the window.
    sh_mask = swing_highs(window["high"], swing_left, swing_right)
    sl_mask = swing_lows(window["low"], swing_left, swing_right)

    last_sh = window["high"][sh_mask].iloc[-1] if sh_mask.any() else None
    last_sl = window["low"][sl_mask].iloc[-1] if sl_mask.any() else None

    if last_sh is not None and latest["high"] > last_sh and latest["close"] < last_sh:
        return LiquiditySweep(
            direction="bearish",
            swept_level=float(last_sh),
            sweep_extreme=float(latest["high"]),
            bar_index=bars.index[-1],
        )

    if last_sl is not None and latest["low"] < last_sl and latest["close"] > last_sl:
        return LiquiditySweep(
            direction="bullish",
            swept_level=float(last_sl),
            sweep_extreme=float(latest["low"]),
            bar_index=bars.index[-1],
        )

    return None
