from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

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


class Strategy(ABC):
    @abstractmethod
    def generate_signal(self, symbol: str, bars: pd.DataFrame) -> Signal: ...
