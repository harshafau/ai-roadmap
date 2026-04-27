"""Strategy B: Volume Profile (POC / Value Area) + VWAP confluence.

Mean-reversion at the edges of today's developing value area, with VWAP as a
secondary confluence and RSI as an exhaustion filter:

  - At VAH (value area high) AND price > VWAP AND RSI > rsi_overbought → SELL
  - At VAL (value area low) AND price < VWAP AND RSI < rsi_oversold → BUY

Targets the POC (point of control). Stop just beyond the value-area edge.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..indicators import atr, build_volume_profile, rsi, session_vwap
from .base import Signal, SignalType, Strategy, StrategyContext


@dataclass
class VolumeProfilePocVwapStrategy(Strategy):
    bin_count: int = 30
    value_area_pct: float = 0.70
    proximity_atr_mult: float = 0.5  # how close to VAH/VAL to count as 'at edge'
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    atr_period: int = 14

    def generate_signal(
        self, symbol: str, bars: pd.DataFrame, context: StrategyContext | None = None
    ) -> Signal:
        if len(bars) < max(self.atr_period, self.rsi_period) + 5:
            return Signal(symbol, SignalType.HOLD, float("nan"), "insufficient history")

        # Restrict profile to the current session if we know when it started.
        session = bars
        if isinstance(bars.index, pd.DatetimeIndex):
            today = bars.index[-1].normalize()
            session = bars[bars.index >= today]
            if len(session) < 5:
                return Signal(symbol, SignalType.HOLD, float(bars["close"].iloc[-1]), "session too short")

        vp = build_volume_profile(session, self.bin_count, self.value_area_pct)
        price = float(bars["close"].iloc[-1])
        v = float(session_vwap(bars).iloc[-1])
        a = float(atr(bars, self.atr_period).iloc[-1])
        r = float(rsi(bars["close"], self.rsi_period).iloc[-1])

        proximity = self.proximity_atr_mult * a

        # SELL setup at VAH
        if abs(price - vp.vah) <= proximity and price > v and r > self.rsi_overbought:
            stop = vp.vah + 0.5 * a
            target = vp.poc
            if stop > price > target:
                return Signal(
                    symbol, SignalType.SELL, price,
                    f"VAH={vp.vah:.2f} > VWAP, RSI={r:.1f} overbought; target POC={vp.poc:.2f}",
                    stop_loss=stop, take_profit=target,
                )

        # BUY setup at VAL
        if abs(price - vp.val) <= proximity and price < v and r < self.rsi_oversold:
            stop = vp.val - 0.5 * a
            target = vp.poc
            if stop < price < target:
                return Signal(
                    symbol, SignalType.BUY, price,
                    f"VAL={vp.val:.2f} < VWAP, RSI={r:.1f} oversold; target POC={vp.poc:.2f}",
                    stop_loss=stop, take_profit=target,
                )

        return Signal(symbol, SignalType.HOLD, price, "no value-area edge setup")
