"""Walk-forward backtest runner.

Iterates daily bars one-at-a-time, asks the strategy for a signal on the data
seen so far, fills at next bar's open, and tracks a simple equity curve.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from .dhan_client import Instrument
from .market_data import MarketDataSource
from .strategy import Signal, SignalType, Strategy


@dataclass
class BacktestResult:
    symbol: str
    trades: list[dict] = field(default_factory=list)
    equity_curve: list[tuple[pd.Timestamp, float]] = field(default_factory=list)
    final_equity: float = 0.0
    total_return_pct: float = 0.0

    def summary(self) -> str:
        n = len(self.trades)
        return (
            f"{self.symbol}: trades={n} final_equity={self.final_equity:,.2f} "
            f"return={self.total_return_pct:+.2f}%"
        )


def run_backtest(
    strategy: Strategy,
    data_source: MarketDataSource,
    instrument: Instrument,
    from_date: date,
    to_date: date,
    starting_cash: float = 100_000.0,
    qty_per_trade: int = 10,
) -> BacktestResult:
    bars = data_source.daily_bars(instrument, from_date, to_date)
    result = BacktestResult(symbol=instrument.symbol)
    cash = starting_cash
    position = 0
    avg_price = 0.0

    for i in range(1, len(bars)):
        window = bars.iloc[: i + 1]
        signal: Signal = strategy.generate_signal(instrument.symbol, window)

        if i + 1 < len(bars):
            fill_price = float(bars.iloc[i + 1]["open"])
        else:
            fill_price = float(bars.iloc[i]["close"])

        if signal.type == SignalType.BUY and cash >= fill_price * qty_per_trade:
            cash -= fill_price * qty_per_trade
            new_qty = position + qty_per_trade
            avg_price = (avg_price * position + fill_price * qty_per_trade) / new_qty
            position = new_qty
            result.trades.append({"date": bars.index[i], "side": "BUY", "qty": qty_per_trade, "price": fill_price})
        elif signal.type == SignalType.SELL and position > 0:
            qty = min(qty_per_trade, position)
            cash += fill_price * qty
            position -= qty
            if position == 0:
                avg_price = 0.0
            result.trades.append({"date": bars.index[i], "side": "SELL", "qty": qty, "price": fill_price})

        equity = cash + position * float(bars.iloc[i]["close"])
        result.equity_curve.append((bars.index[i], equity))

    final_close = float(bars.iloc[-1]["close"]) if len(bars) else 0.0
    result.final_equity = cash + position * final_close
    result.total_return_pct = (result.final_equity / starting_cash - 1.0) * 100.0
    return result
