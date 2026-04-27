from datetime import date, timedelta

from trading_bot.risk import DailyLossGuard, position_size


def test_position_size_basic():
    # 1L capital, 1% risk = ₹1000. Stop ₹2 below entry → 500 shares.
    qty = position_size(100_000, 1.0, entry=100.0, stop=98.0)
    assert qty == 500


def test_position_size_zero_when_stop_at_entry():
    assert position_size(100_000, 1.0, entry=100.0, stop=100.0) == 0


def test_daily_loss_guard_trips_at_threshold():
    g = DailyLossGuard(starting_capital=1_000_000, max_loss_pct=3.0)
    today = date(2024, 1, 1)
    assert g.can_trade(today)
    g.record_pnl(today, -10_000)
    assert g.can_trade(today)
    g.record_pnl(today, -25_000)  # -35k > -30k threshold
    assert not g.can_trade(today)


def test_daily_loss_guard_resets_next_day():
    g = DailyLossGuard(starting_capital=1_000_000, max_loss_pct=3.0)
    g.record_pnl(date(2024, 1, 1), -50_000)
    assert not g.can_trade(date(2024, 1, 1))
    assert g.can_trade(date(2024, 1, 2))
