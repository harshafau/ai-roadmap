"""APScheduler wiring. Runs the daily strategy loop on the configured cron."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import StrategyConfig
from .executor.base import OrderRouter
from .market_data import MarketDataSource
from .dhan_client import Instrument
from .strategy import Strategy, SignalType

log = logging.getLogger(__name__)


def run_once(
    strategy: Strategy,
    data_source: MarketDataSource,
    router: OrderRouter,
    config: StrategyConfig,
    instruments: dict[str, Instrument],
    qty_per_trade: int = 10,
) -> None:
    today = date.today()
    lookback_days = max(config.strategy.slow_period * 3, 200)
    start = today - timedelta(days=lookback_days)

    for item in config.watchlist:
        inst = instruments[item.symbol]
        bars = data_source.daily_bars(inst, start, today)
        signal = strategy.generate_signal(item.symbol, bars)
        log.info("signal %s -> %s (%s)", item.symbol, signal.type.value, signal.reason)
        if signal.type != SignalType.HOLD:
            router.route(signal, qty_per_trade)


def start_scheduler(
    strategy: Strategy,
    data_source: MarketDataSource,
    router: OrderRouter,
    config: StrategyConfig,
    instruments: dict[str, Instrument],
) -> None:
    sched = BlockingScheduler(timezone=config.schedule.timezone)
    trigger = CronTrigger.from_crontab(config.schedule.cron, timezone=config.schedule.timezone)
    sched.add_job(
        run_once,
        trigger=trigger,
        args=[strategy, data_source, router, config, instruments],
        id="daily_strategy",
    )
    log.info("scheduler starting; cron=%r tz=%s", config.schedule.cron, config.schedule.timezone)
    sched.start()
