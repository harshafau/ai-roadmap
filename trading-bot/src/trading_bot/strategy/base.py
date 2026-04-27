from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class Signal:
    symbol: str
    type: SignalType
    price: float
    reason: str
    stop_loss: float | None = None
    take_profit: float | None = None


@dataclass
class StrategyContext:
    """Optional auxiliary inputs a strategy may consume.

    `book` is a Dhan 5-level depth snapshot ({"bids":[(price,qty),..], "asks":[..]}).
    `session_start` marks the first bar of the current trading session (for intraday
    indicators like VWAP that anchor at session open).
    """
    book: dict[str, Any] | None = None
    session_start: pd.Timestamp | None = None


class Strategy(ABC):
    @abstractmethod
    def generate_signal(
        self,
        symbol: str,
        bars: pd.DataFrame,
        context: StrategyContext | None = None,
    ) -> Signal: ...
