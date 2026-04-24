from __future__ import annotations

from abc import ABC, abstractmethod

from ..strategy import Signal


class OrderRouter(ABC):
    @abstractmethod
    def route(self, signal: Signal, qty: int) -> None: ...
