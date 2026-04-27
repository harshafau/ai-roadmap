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
    def intraday_bars(
        self, instrument: Instrument, from_date: date, to_date: date, interval_minutes: int
    ) -> pd.DataFrame: ...


@dataclass
class DhanMarketData:
    client: DhanClient

    def daily_bars(self, instrument: Instrument, from_date: date, to_date: date) -> pd.DataFrame:
        return self.client.historical_daily(instrument, from_date, to_date)

    def intraday_bars(
        self, instrument: Instrument, from_date: date, to_date: date, interval_minutes: int = 5
    ) -> pd.DataFrame:
        return self.client.intraday_minute(instrument, from_date, to_date, interval_minutes)


@dataclass
class SyntheticMarketData:
    """Generates deterministic OHLC bars without hitting any network."""

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

    def intraday_bars(
        self, instrument: Instrument, from_date: date, to_date: date, interval_minutes: int = 5
    ) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed + hash(instrument.symbol) % 10_000)
        # Build NSE-style intraday sessions: 09:15 -> 15:30 IST per business day.
        bars_per_day = (6 * 60 + 15) // interval_minutes  # 75 bars at 5-min
        days = pd.bdate_range(from_date, to_date)
        if len(days) == 0:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        timestamps: list[pd.Timestamp] = []
        for d in days:
            base = pd.Timestamp(d).replace(hour=9, minute=15)
            for i in range(bars_per_day):
                timestamps.append(base + pd.Timedelta(minutes=i * interval_minutes))

        n = len(timestamps)
        # Smaller bar-level vol than daily.
        returns = rng.normal(self.drift / bars_per_day, self.vol / np.sqrt(bars_per_day), n)
        price = 1000.0 * np.exp(np.cumsum(returns))
        opens = np.empty(n)
        opens[0] = price[0] * (1 + rng.normal(0, 0.0005))
        opens[1:] = price[:-1]  # next bar opens at previous close
        highs = np.maximum(opens, price) * (1 + np.abs(rng.normal(0, 0.001, n)))
        lows = np.minimum(opens, price) * (1 - np.abs(rng.normal(0, 0.001, n)))
        volumes = rng.integers(5_000, 50_000, n)
        return pd.DataFrame(
            {"open": opens, "high": highs, "low": lows, "close": price, "volume": volumes},
            index=pd.DatetimeIndex(timestamps, name="timestamp"),
        )
