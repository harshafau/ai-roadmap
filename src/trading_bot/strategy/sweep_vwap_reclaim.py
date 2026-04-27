"""Strategy A: Liquidity Sweep + VWAP reclaim, with ATR/RSI confluence and an
order-flow proxy from volume delta + book imbalance.

Logic on the latest closed 5-min bar:

  1. A liquidity sweep occurred (bullish = wick below recent swing low + close back
     above; bearish = mirror).
  2. Price has reclaimed VWAP in the sweep direction (close above VWAP for bullish
     sweep, below for bearish).
  3. ATR > min_atr_pct of price (avoid dead bars).
  4. RSI in agreeing zone (>50 for longs, <50 for shorts).
  5. Order-flow proxy agrees: cumulative volume delta over last `flow_lookback`
     bars same sign as the trade, OR book imbalance (if provided) same sign.

Stop = sweep wick extreme, padded by stop_atr_mult * ATR.
Target = entry +/- target_R * (entry - stop) for longs/shorts.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..indicators import atr, book_imbalance, rsi, session_vwap, volume_delta
from ..patterns import detect_liquidity_sweep
from .base import Signal, SignalType, Strategy, StrategyContext


@dataclass
class SweepVwapReclaimStrategy(Strategy):
    swing_lookback: int = 20
    atr_period: int = 14
    rsi_period: int = 14
    min_atr_pct: float = 0.001        # ATR / price >= 0.1%
    flow_lookback: int = 10
    stop_atr_mult: float = 0.2
    target_r: float = 1.5

    def generate_signal(
        self, symbol: str, bars: pd.DataFrame, context: StrategyContext | None = None
    ) -> Signal:
        if len(bars) < max(self.swing_lookback, self.atr_period, self.rsi_period) + 5:
            return Signal(symbol, SignalType.HOLD, float("nan"), "insufficient history")

        sweep = detect_liquidity_sweep(bars, lookback=self.swing_lookback)
        if sweep is None:
            return Signal(symbol, SignalType.HOLD, float(bars["close"].iloc[-1]), "no sweep")

        price = float(bars["close"].iloc[-1])
        v = float(session_vwap(bars).iloc[-1])
        a = float(atr(bars, self.atr_period).iloc[-1])
        r = float(rsi(bars["close"], self.rsi_period).iloc[-1])

        if a / price < self.min_atr_pct:
            return Signal(symbol, SignalType.HOLD, price, "atr too small")

        delta_sum = float(volume_delta(bars).iloc[-self.flow_lookback :].sum())
        book_signal = book_imbalance(context.book if context else None)

        if sweep.direction == "bullish":
            if price <= v:
                return Signal(symbol, SignalType.HOLD, price, "vwap not reclaimed up")
            if r <= 50:
                return Signal(symbol, SignalType.HOLD, price, "rsi not bullish")
            if delta_sum <= 0 and book_signal <= 0:
                return Signal(symbol, SignalType.HOLD, price, "order-flow proxy disagrees")
            stop = sweep.sweep_extreme - self.stop_atr_mult * a
            risk = price - stop
            target = price + self.target_r * risk
            return Signal(
                symbol, SignalType.BUY, price,
                f"bullish sweep@{sweep.swept_level:.2f} + vwap reclaim",
                stop_loss=stop, take_profit=target,
            )

        # bearish
        if price >= v:
            return Signal(symbol, SignalType.HOLD, price, "vwap not reclaimed down")
        if r >= 50:
            return Signal(symbol, SignalType.HOLD, price, "rsi not bearish")
        if delta_sum >= 0 and book_signal >= 0:
            return Signal(symbol, SignalType.HOLD, price, "order-flow proxy disagrees")
        stop = sweep.sweep_extreme + self.stop_atr_mult * a
        risk = stop - price
        target = price - self.target_r * risk
        return Signal(
            symbol, SignalType.SELL, price,
            f"bearish sweep@{sweep.swept_level:.2f} + vwap reject",
            stop_loss=stop, take_profit=target,
        )
