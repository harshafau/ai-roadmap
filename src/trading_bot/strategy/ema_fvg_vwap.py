"""Strategy C: EMA trend + FVG retest + VWAP filter.

Trend filter: 50-EMA on close. Price > EMA AND price > VWAP → bull bias.
Mirror for bear bias.

Entry: latest bar retests an unfilled fair-value gap aligned with the trend.
  - Bull bias + bullish FVG: bar's low <= FVG.top AND close > FVG.bottom → BUY
  - Bear bias + bearish FVG: bar's high >= FVG.bottom AND close < FVG.top → SELL

Stop just beyond the far edge of the FVG. Target = `target_r` * risk.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..indicators import ema, session_vwap
from ..patterns import latest_unfilled_fvg
from .base import Signal, SignalType, Strategy, StrategyContext


@dataclass
class EmaFvgVwapStrategy(Strategy):
    ema_period: int = 50
    fvg_lookback: int = 50
    target_r: float = 2.0

    def generate_signal(
        self, symbol: str, bars: pd.DataFrame, context: StrategyContext | None = None
    ) -> Signal:
        if len(bars) < self.ema_period + 5:
            return Signal(symbol, SignalType.HOLD, float("nan"), "insufficient history")

        price = float(bars["close"].iloc[-1])
        e = float(ema(bars["close"], self.ema_period).iloc[-1])
        v = float(session_vwap(bars).iloc[-1])
        latest = bars.iloc[-1]

        bull_bias = price > e and price > v
        bear_bias = price < e and price < v

        if bull_bias:
            fvg = latest_unfilled_fvg(bars, "bullish", self.fvg_lookback)
            if fvg and latest["low"] <= fvg.top and latest["close"] > fvg.bottom:
                stop = fvg.bottom * 0.999
                risk = price - stop
                if risk <= 0:
                    return Signal(symbol, SignalType.HOLD, price, "invalid stop")
                target = price + self.target_r * risk
                return Signal(
                    symbol, SignalType.BUY, price,
                    f"bull-bias retest of FVG[{fvg.bottom:.2f}-{fvg.top:.2f}]",
                    stop_loss=stop, take_profit=target,
                )

        if bear_bias:
            fvg = latest_unfilled_fvg(bars, "bearish", self.fvg_lookback)
            if fvg and latest["high"] >= fvg.bottom and latest["close"] < fvg.top:
                stop = fvg.top * 1.001
                risk = stop - price
                if risk <= 0:
                    return Signal(symbol, SignalType.HOLD, price, "invalid stop")
                target = price - self.target_r * risk
                return Signal(
                    symbol, SignalType.SELL, price,
                    f"bear-bias retest of FVG[{fvg.bottom:.2f}-{fvg.top:.2f}]",
                    stop_loss=stop, take_profit=target,
                )

        return Signal(symbol, SignalType.HOLD, price, "no FVG retest in trend")
