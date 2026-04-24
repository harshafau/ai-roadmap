from __future__ import annotations

import logging
from dataclasses import dataclass

from ..portfolio import Portfolio
from ..strategy import Signal, SignalType
from .base import OrderRouter

log = logging.getLogger(__name__)


@dataclass
class PaperExecutor(OrderRouter):
    portfolio: Portfolio

    def route(self, signal: Signal, qty: int) -> None:
        if signal.type == SignalType.HOLD or qty <= 0:
            return
        order = self.portfolio.apply_fill(
            symbol=signal.symbol,
            side=signal.type.value,
            qty=qty,
            price=signal.price,
            mode="paper",
            reason=signal.reason,
        )
        log.info("PAPER %s %s qty=%s @ %.2f (%s)", order.side, order.symbol, order.qty, order.price, order.reason)
