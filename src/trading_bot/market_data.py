"""Market-data helpers.

Provides a `MarketDataSource` protocol plus two implementations:
- `DhanMarketData`: real data via DhanClient (requires credentials).
- `SyntheticMarketData`: deterministic OHLC series for backtests without creds.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Protocol

import numpy as np
import pandas as pd

from .dhan_client import DhanClient, Instrument


class MarketDataSource(Protocol):
    def daily_bars(self, instrument: Instrument, from_date: date, to_date: date) -> pd.DataFrame: ...


@dataclass
class DhanMarketData:
    client: DhanClient

    def daily_bars(self, instrument: Instrument, from_date: date, to_date: date) -> pd.DataFrame:
        return self.client.historical_daily(instrument, from_date, to_date)


@dataclass
class SyntheticMarketData:
    """Generates deterministic OHLC bars. Handy for running a backtest end-to-end
    without hitting the network or needing Dhan credentials."""

    seed: int = 42
    drift: float = 0.0005
    vol: float = 0.015

    def daily_bars(self, instrument: Instrument, from_date: date, to_date: date) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed + hash(instrument.symbol) % 10_000)
        days = pd.bdate_range(from_date, to_date)
        n = len(days)
        if n == 0:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        returns = rng.normal(self.drift, self.vol, n)
        price = 1000.0 * np.exp(np.cumsum(returns))
        opens = price * (1 + rng.normal(0, 0.002, n))
        highs = np.maximum(opens, price) * (1 + np.abs(rng.normal(0, 0.003, n)))
        lows = np.minimum(opens, price) * (1 - np.abs(rng.normal(0, 0.003, n)))
        volumes = rng.integers(50_000, 500_000, n)
        return pd.DataFrame(
            {"open": opens, "high": highs, "low": lows, "close": price, "volume": volumes},
            index=days,
        )
