from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .base import Signal, SignalType, Strategy


@dataclass
class MACrossoverStrategy(Strategy):
    """Simple fast/slow SMA crossover on close prices.

    BUY when fast SMA crosses above slow SMA on the latest bar.
    SELL when fast SMA crosses below slow SMA on the latest bar.
    HOLD otherwise.
    """

    fast_period: int = 20
    slow_period: int = 50

    def __post_init__(self) -> None:
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be strictly less than slow_period")

    def generate_signal(self, symbol: str, bars: pd.DataFrame) -> Signal:
        if len(bars) < self.slow_period + 1:
            return Signal(symbol, SignalType.HOLD, float("nan"), "insufficient history")

        close = bars["close"]
        fast = close.rolling(self.fast_period).mean()
        slow = close.rolling(self.slow_period).mean()

        prev_diff = fast.iloc[-2] - slow.iloc[-2]
        curr_diff = fast.iloc[-1] - slow.iloc[-1]
        price = float(close.iloc[-1])

        if prev_diff <= 0 and curr_diff > 0:
            return Signal(symbol, SignalType.BUY, price, f"fast({self.fast_period}) crossed above slow({self.slow_period})")
        if prev_diff >= 0 and curr_diff < 0:
            return Signal(symbol, SignalType.SELL, price, f"fast({self.fast_period}) crossed below slow({self.slow_period})")
        return Signal(symbol, SignalType.HOLD, price, "no crossover")
