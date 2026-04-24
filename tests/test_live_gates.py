import pytest

from trading_bot.config import ExecutionMode, Settings
from trading_bot.dhan_client import Instrument
from trading_bot.executor.live import LiveExecutor
from trading_bot.strategy import Signal, SignalType


class _FakeClient:
    def __init__(self):
        class _SDK: pass
        self._sdk = _SDK()


def _sig() -> Signal:
    return Signal("X", SignalType.BUY, 100.0, "t")


def test_refuses_when_mode_not_live():
    settings = Settings(execution_mode=ExecutionMode.PAPER)
    ex = LiveExecutor(
        client=_FakeClient(),
        instruments={"X": Instrument("X", "NSE_EQ", "STUB-X")},
        settings=settings,
        confirmed=True,
    )
    with pytest.raises(RuntimeError, match="EXECUTION_MODE"):
        ex.route(_sig(), 10)


def test_refuses_when_not_confirmed():
    settings = Settings(execution_mode=ExecutionMode.LIVE)
    ex = LiveExecutor(
        client=_FakeClient(),
        instruments={"X": Instrument("X", "NSE_EQ", "STUB-X")},
        settings=settings,
        confirmed=False,
    )
    with pytest.raises(RuntimeError, match="i-understand-live-trading"):
        ex.route(_sig(), 10)
