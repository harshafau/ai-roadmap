"""Smoke tests for the three composite strategies. We verify they run
end-to-end on synthetic data without errors and produce well-formed Signals.
"""
from datetime import date

import pandas as pd

from trading_bot.dhan_client import Instrument
from trading_bot.market_data import SyntheticMarketData
from trading_bot.strategy import (
    EmaFvgVwapStrategy,
    SignalType,
    SweepVwapReclaimStrategy,
    VolumeProfilePocVwapStrategy,
)


def _bars():
    return SyntheticMarketData(seed=7).intraday_bars(
        Instrument("X", "NSE_EQ", "STUB-X"), date(2024, 1, 1), date(2024, 1, 10), 5
    )


def test_sweep_strategy_returns_signal():
    sig = SweepVwapReclaimStrategy().generate_signal("X", _bars())
    assert sig.type in {SignalType.BUY, SignalType.SELL, SignalType.HOLD}
    if sig.type != SignalType.HOLD:
        assert sig.stop_loss is not None and sig.take_profit is not None


def test_volume_profile_strategy_returns_signal():
    sig = VolumeProfilePocVwapStrategy().generate_signal("X", _bars())
    assert sig.type in {SignalType.BUY, SignalType.SELL, SignalType.HOLD}


def test_ema_fvg_strategy_returns_signal():
    sig = EmaFvgVwapStrategy().generate_signal("X", _bars())
    assert sig.type in {SignalType.BUY, SignalType.SELL, SignalType.HOLD}


def test_strategies_handle_short_history_gracefully():
    short = _bars().head(10)
    for strat in (
        SweepVwapReclaimStrategy(),
        VolumeProfilePocVwapStrategy(),
        EmaFvgVwapStrategy(),
    ):
        sig = strat.generate_signal("X", short)
        assert sig.type == SignalType.HOLD
