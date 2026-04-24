import numpy as np
import pandas as pd
import pytest

from trading_bot.strategy import MACrossoverStrategy, SignalType


def _bars(closes: list[float]) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="B")
    return pd.DataFrame({"open": closes, "high": closes, "low": closes, "close": closes, "volume": [1] * len(closes)}, index=idx)


def test_rejects_invalid_periods():
    with pytest.raises(ValueError):
        MACrossoverStrategy(fast_period=50, slow_period=50)


def test_hold_when_insufficient_history():
    s = MACrossoverStrategy(fast_period=3, slow_period=5)
    sig = s.generate_signal("X", _bars([1, 2, 3]))
    assert sig.type == SignalType.HOLD


def test_buy_on_golden_cross():
    # Flat history then one sharp up bar → fast SMA crosses above slow on the latest bar.
    closes = [100.0] * 15 + [200.0]
    s = MACrossoverStrategy(fast_period=3, slow_period=8)
    sig = s.generate_signal("X", _bars(closes))
    assert sig.type == SignalType.BUY
    assert "crossed above" in sig.reason


def test_sell_on_death_cross():
    # Flat history then one sharp down bar → fast SMA crosses below slow on the latest bar.
    closes = [100.0] * 15 + [1.0]
    s = MACrossoverStrategy(fast_period=3, slow_period=8)
    sig = s.generate_signal("X", _bars(closes))
    assert sig.type == SignalType.SELL
    assert "crossed below" in sig.reason


def test_hold_when_no_crossover():
    closes = list(np.linspace(100, 200, 40))  # monotonic uptrend → no crossover at end
    s = MACrossoverStrategy(fast_period=5, slow_period=20)
    sig = s.generate_signal("X", _bars(closes))
    assert sig.type == SignalType.HOLD
