from trading_bot.executor import PaperExecutor
from trading_bot.portfolio import Portfolio
from trading_bot.strategy import Signal, SignalType


def test_paper_executor_records_fill(tmp_path):
    db = f"sqlite:///{tmp_path/'t.db'}"
    p = Portfolio(db, starting_cash=100_000)
    ex = PaperExecutor(portfolio=p)

    ex.route(Signal("X", SignalType.BUY, 100.0, "test"), 10)
    assert len(list(p.orders())) == 1

    # HOLD and qty=0 must not record anything.
    ex.route(Signal("X", SignalType.HOLD, 100.0, "test"), 10)
    ex.route(Signal("X", SignalType.BUY, 100.0, "test"), 0)
    assert len(list(p.orders())) == 1
