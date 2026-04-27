from datetime import date

from trading_bot.backtest import run_backtest
from trading_bot.dhan_client import Instrument
from trading_bot.market_data import SyntheticMarketData
from trading_bot.strategy import MACrossoverStrategy


def test_end_to_end_synthetic_daily_backtest_runs():
    strat = MACrossoverStrategy(fast_period=10, slow_period=30)
    source = SyntheticMarketData(seed=1)
    inst = Instrument("RELIANCE", "NSE_EQ", "STUB-RELIANCE")
    result = run_backtest(strat, source, inst, date(2023, 1, 1), date(2024, 12, 31))

    assert result.symbol == "RELIANCE"
    assert len(result.equity_curve) > 100
    assert isinstance(result.final_equity, float)
    assert "RELIANCE" in result.summary()


def test_intraday_backtest_runs_without_error():
    from trading_bot.strategy import EmaFvgVwapStrategy

    strat = EmaFvgVwapStrategy()
    source = SyntheticMarketData(seed=3)
    inst = Instrument("INFY", "NSE_EQ", "STUB-INFY")
    result = run_backtest(
        strat, source, inst, date(2024, 1, 1), date(2024, 1, 10),
        starting_cash=1_000_000, risk_pct=1.0, interval_minutes=5,
    )
    assert isinstance(result.win_rate, float)
    assert isinstance(result.max_drawdown_pct, float)
