"""Position sizing + daily loss guard."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


def position_size(capital: float, risk_pct: float, entry: float, stop: float) -> int:
    """Whole-share quantity such that loss-at-stop ≈ capital * risk_pct/100.

    Returns 0 if the stop is at/through the entry (invalid setup).
    """
    risk_per_share = abs(entry - stop)
    if risk_per_share <= 0 or capital <= 0 or risk_pct <= 0:
        return 0
    risk_inr = capital * (risk_pct / 100.0)
    return int(risk_inr // risk_per_share)


@dataclass
class DailyLossGuard:
    """Stops trading for the rest of the day once realized P&L breaches threshold.

    `max_loss_pct` is a percentage of starting capital. P&L is supplied externally
    by whoever updates positions (paper executor in paper mode, fill events in live).
    """
    starting_capital: float
    max_loss_pct: float = 3.0
    _today: date | None = None
    _realized_pnl_today: float = 0.0
    _tripped: bool = False

    def _maybe_reset(self, today: date) -> None:
        if self._today != today:
            self._today = today
            self._realized_pnl_today = 0.0
            self._tripped = False

    def record_pnl(self, today: date, realized_pnl: float) -> None:
        self._maybe_reset(today)
        self._realized_pnl_today += realized_pnl
        threshold = -abs(self.starting_capital) * (self.max_loss_pct / 100.0)
        if self._realized_pnl_today <= threshold:
            self._tripped = True

    def can_trade(self, today: date) -> bool:
        self._maybe_reset(today)
        return not self._tripped

    def realized_today(self, today: date) -> float:
        self._maybe_reset(today)
        return self._realized_pnl_today
