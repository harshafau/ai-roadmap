from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ..portfolio import Portfolio
from ..risk import position_size
from ..strategy import Signal, SignalType
from .base import OrderRouter

log = logging.getLogger(__name__)


@dataclass
class PaperExecutor(OrderRouter):
    portfolio: Portfolio
    risk_pct: float = 1.0
    fixed_qty: int | None = None  # if set, overrides risk-based sizing
    capital_override: float | None = None  # else uses portfolio.starting_cash()

    def route(self, signal: Signal, qty: int) -> None:
        if signal.type == SignalType.HOLD:
            return
        if qty <= 0:
            qty = self._size(signal)
        if qty <= 0:
            log.debug("skip %s %s: qty=0 (no stop or invalid risk)", signal.type.value, signal.symbol)
            return
        order = self.portfolio.apply_fill(
            symbol=signal.symbol,
            side=signal.type.value,
            qty=qty,
            price=signal.price,
            mode="paper",
            reason=signal.reason,
        )
        log.info(
            "PAPER %s %s qty=%s @ %.2f stop=%s target=%s (%s)",
            order.side, order.symbol, order.qty, order.price,
            f"{signal.stop_loss:.2f}" if signal.stop_loss else "-",
            f"{signal.take_profit:.2f}" if signal.take_profit else "-",
            order.reason,
        )

    def _size(self, signal: Signal) -> int:
        if self.fixed_qty is not None:
            return self.fixed_qty
        if signal.stop_loss is None:
            return 0
        capital = self.capital_override or self.portfolio.starting_cash()
        return position_size(capital, self.risk_pct, signal.price, signal.stop_loss)
