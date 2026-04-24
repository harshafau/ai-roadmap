"""Real Dhan order placement. DISABLED by default.

Two gates must be open to send a real order:
  1. settings.execution_mode == ExecutionMode.LIVE
  2. the CLI flag `--i-understand-live-trading` was passed, which sets
     `confirmed=True` on the constructor.

Either gate closed => this raises RuntimeError, not a warning.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from ..config import ExecutionMode, Settings
from ..dhan_client import DhanClient, Instrument
from ..strategy import Signal, SignalType
from .base import OrderRouter

log = logging.getLogger(__name__)


@dataclass
class LiveExecutor(OrderRouter):
    client: DhanClient
    instruments: dict[str, Instrument]
    settings: Settings
    confirmed: bool = False

    def route(self, signal: Signal, qty: int) -> None:
        if signal.type == SignalType.HOLD or qty <= 0:
            return
        if self.settings.execution_mode != ExecutionMode.LIVE:
            raise RuntimeError("LiveExecutor invoked but EXECUTION_MODE != 'live'")
        if not self.confirmed:
            raise RuntimeError("LiveExecutor invoked without --i-understand-live-trading")

        inst = self.instruments[signal.symbol]
        # NOTE: Real order placement. Change MARKET -> LIMIT + price if you
        # want explicit price control. Product type CNC = delivery.
        resp = self.client._sdk.place_order(  # type: ignore[attr-defined]
            security_id=inst.security_id,
            exchange_segment=inst.exchange,
            transaction_type=signal.type.value,
            quantity=qty,
            order_type="MARKET",
            product_type="CNC",
            price=0,
        )
        log.warning("LIVE order sent: %s %s qty=%s -> %s", signal.type.value, signal.symbol, qty, resp)
