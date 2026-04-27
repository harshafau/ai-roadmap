"""APScheduler wiring. Cron expression decides cadence (daily EOD or intraday)."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import StrategyConfig
from .dhan_client import Instrument
from .executor.base import OrderRouter
from .market_data import MarketDataSource
from .risk import DailyLossGuard
from .strategy import SignalType, Strategy, StrategyContext

log = logging.getLogger(__name__)


def run_once(
    strategy: Strategy,
    data_source: MarketDataSource,
    router: OrderRouter,
    config: StrategyConfig,
    instruments: list[Instrument],
    guard: DailyLossGuard | None = None,
) -> None:
    today = date.today()
    if guard and not guard.can_trade(today):
        log.warning("daily loss guard tripped; skipping run")
        return

    interval = config.schedule.bar_interval_minutes
    if interval > 0:
        # ~5 sessions of intraday bars is plenty for 50/14-period indicators.
        start = today - timedelta(days=10)
        fetch = lambda inst: data_source.intraday_bars(inst, start, today, interval)
    else:
        start = today - timedelta(days=max(config.strategy.slow_period * 3, 200))
        fetch = lambda inst: data_source.daily_bars(inst, start, today)

    for inst in instruments:
        try:
            bars = fetch(inst)
        except Exception as exc:
            log.exception("data fetch failed for %s: %s", inst.symbol, exc)
            continue
        if len(bars) < 50:
            continue
        signal = strategy.generate_signal(inst.symbol, bars, StrategyContext())
        log.info("signal %s -> %s (%s)", inst.symbol, signal.type.value, signal.reason)
        if signal.type != SignalType.HOLD:
            router.route(signal, qty=0)  # router decides qty from stop/risk


def start_scheduler(
    strategy: Strategy,
    data_source: MarketDataSource,
    router: OrderRouter,
    config: StrategyConfig,
    instruments: list[Instrument],
    guard: DailyLossGuard | None = None,
) -> None:
    sched = BlockingScheduler(timezone=config.schedule.timezone)
    trigger = CronTrigger.from_crontab(config.schedule.cron, timezone=config.schedule.timezone)
    sched.add_job(
        run_once,
        trigger=trigger,
        args=[strategy, data_source, router, config, instruments, guard],
        id="strategy_loop",
    )
    log.info("scheduler starting; cron=%r tz=%s", config.schedule.cron, config.schedule.timezone)
    sched.start()
