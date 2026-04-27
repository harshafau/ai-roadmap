"""Walk-forward backtest runner.

Iterates bars one at a time, asks the strategy for a signal on the data seen so
far. Long flow:
  - On BUY with stop/target → open a long, fill at next bar open. Exit if a
    later bar's range hits stop or target.
  - On SELL → mirror for shorts (allowed if `allow_short=True`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from .dhan_client import Instrument
from .market_data import MarketDataSource
from .risk import position_size
from .strategy import Signal, SignalType, Strategy


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    side: str
    qty: int
    entry: float
    exit: float
    pnl: float
    reason_in: str
    reason_out: str


@dataclass
class BacktestResult:
    symbol: str
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[tuple[pd.Timestamp, float]] = field(default_factory=list)
    final_equity: float = 0.0
    total_return_pct: float = 0.0
    win_rate: float = 0.0
    expectancy: float = 0.0     # average pnl per trade
    max_drawdown_pct: float = 0.0
    sharpe: float = 0.0          # crude: mean(daily-returns) / std

    def summary(self) -> str:
        return (
            f"{self.symbol}: trades={len(self.trades)} "
            f"final_equity={self.final_equity:,.2f} return={self.total_return_pct:+.2f}% "
            f"win_rate={self.win_rate*100:.1f}% expectancy={self.expectancy:+.2f} "
            f"max_dd={self.max_drawdown_pct:.2f}% sharpe={self.sharpe:.2f}"
        )


def _compute_metrics(result: BacktestResult, starting_cash: float) -> None:
    n = len(result.trades)
    wins = [t for t in result.trades if t.pnl > 0]
    result.win_rate = len(wins) / n if n else 0.0
    result.expectancy = sum(t.pnl for t in result.trades) / n if n else 0.0

    if result.equity_curve:
        peak = starting_cash
        max_dd = 0.0
        for _, eq in result.equity_curve:
            peak = max(peak, eq)
            dd = (peak - eq) / peak
            max_dd = max(max_dd, dd)
        result.max_drawdown_pct = max_dd * 100.0

        eq_series = pd.Series([eq for _, eq in result.equity_curve])
        rets = eq_series.pct_change().dropna()
        if len(rets) > 1 and rets.std() > 0:
            # Annualisation factor depends on bar frequency; we use raw mean/std
            # for a relative comparison only.
            result.sharpe = float(rets.mean() / rets.std() * math.sqrt(len(rets)))


def run_backtest(
    strategy: Strategy,
    data_source: MarketDataSource,
    instrument: Instrument,
    from_date: date,
    to_date: date,
    starting_cash: float = 1_000_000.0,
    risk_pct: float = 1.0,
    interval_minutes: int = 0,            # 0 = daily, else intraday minutes
    allow_short: bool = True,
) -> BacktestResult:
    if interval_minutes > 0:
        bars = data_source.intraday_bars(instrument, from_date, to_date, interval_minutes)
    else:
        bars = data_source.daily_bars(instrument, from_date, to_date)

    result = BacktestResult(symbol=instrument.symbol)
    cash = starting_cash
    pos_qty = 0
    pos_side: str | None = None
    pos_entry = 0.0
    pos_stop = 0.0
    pos_target = 0.0
    pos_entry_time: pd.Timestamp | None = None
    pos_reason_in = ""

    for i in range(1, len(bars)):
        bar = bars.iloc[i]

        # Check stop/target first using the bar's range.
        if pos_qty > 0 and pos_side is not None:
            hit_stop = (pos_side == "BUY" and bar["low"] <= pos_stop) or (
                pos_side == "SELL" and bar["high"] >= pos_stop
            )
            hit_target = (pos_side == "BUY" and bar["high"] >= pos_target) or (
                pos_side == "SELL" and bar["low"] <= pos_target
            )
            if hit_stop or hit_target:
                exit_price = pos_stop if hit_stop else pos_target
                pnl = (exit_price - pos_entry) * pos_qty if pos_side == "BUY" else (pos_entry - exit_price) * pos_qty
                cash += pnl
                result.trades.append(
                    Trade(
                        entry_time=pos_entry_time,
                        exit_time=bars.index[i],
                        side=pos_side,
                        qty=pos_qty,
                        entry=pos_entry,
                        exit=exit_price,
                        pnl=pnl,
                        reason_in=pos_reason_in,
                        reason_out="stop" if hit_stop else "target",
                    )
                )
                pos_qty = 0
                pos_side = None

        # New signals only if flat.
        if pos_qty == 0:
            window = bars.iloc[: i + 1]
            sig: Signal = strategy.generate_signal(instrument.symbol, window)
            if sig.type != SignalType.HOLD and sig.stop_loss and sig.take_profit:
                if sig.type == SignalType.SELL and not allow_short:
                    pass
                else:
                    fill = float(bars.iloc[i + 1]["open"]) if i + 1 < len(bars) else float(bar["close"])
                    qty = position_size(cash, risk_pct, fill, sig.stop_loss)
                    if qty > 0:
                        pos_qty = qty
                        pos_side = sig.type.value
                        pos_entry = fill
                        pos_stop = sig.stop_loss
                        pos_target = sig.take_profit
                        pos_entry_time = bars.index[i + 1] if i + 1 < len(bars) else bars.index[i]
                        pos_reason_in = sig.reason

        unrealized = 0.0
        if pos_qty > 0 and pos_side is not None:
            mtm = float(bar["close"])
            unrealized = (mtm - pos_entry) * pos_qty if pos_side == "BUY" else (pos_entry - mtm) * pos_qty
        result.equity_curve.append((bars.index[i], cash + unrealized))

    result.final_equity = result.equity_curve[-1][1] if result.equity_curve else starting_cash
    result.total_return_pct = (result.final_equity / starting_cash - 1.0) * 100.0
    _compute_metrics(result, starting_cash)
    return result
