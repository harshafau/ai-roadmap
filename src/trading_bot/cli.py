"""Typer CLI.

    trading-bot list-strategies
    trading-bot backtest --symbol RELIANCE --strategy sweep_vwap_reclaim --from 2024-01-01 --to 2024-12-31 --interval 5
    trading-bot run --dry
    trading-bot run --i-understand-live-trading
    trading-bot status
"""
from __future__ import annotations

import logging
from datetime import datetime
from inspect import signature

import typer
from rich.console import Console
from rich.table import Table

from .backtest import run_backtest
from .config import ExecutionMode, Settings, load_strategy_config
from .dhan_client import Instrument
from .executor import LiveExecutor, PaperExecutor
from .market_data import DhanMarketData, SyntheticMarketData
from .notifications import TelegramNotifier
from .portfolio import Portfolio
from .risk import DailyLossGuard
from .strategy import STRATEGIES
from .universe import load_universe, universe_path

app = typer.Typer(add_completion=False, help="Paper-first Dhan trading bot")
console = Console()


def _setup_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def _build_strategy(name: str, **params):
    if name not in STRATEGIES:
        raise typer.BadParameter(f"unknown strategy '{name}'. Try: {', '.join(STRATEGIES)}")
    cls = STRATEGIES[name]
    accepted = set(signature(cls).parameters.keys())
    return cls(**{k: v for k, v in params.items() if k in accepted})


def _resolve_instruments(cfg) -> list[Instrument]:
    if cfg.universe:
        return load_universe(universe_path(cfg.universe))
    if cfg.watchlist:
        return [Instrument(symbol=w.symbol, exchange=w.exchange, security_id=f"STUB-{w.symbol}") for w in cfg.watchlist]
    raise typer.BadParameter("config has neither `universe` nor `watchlist`")


@app.command("list-strategies")
def list_strategies() -> None:
    tbl = Table(title="Available strategies")
    tbl.add_column("Name"); tbl.add_column("Class")
    for name, cls in STRATEGIES.items():
        tbl.add_row(name, cls.__name__)
    console.print(tbl)


@app.command()
def backtest(
    symbol: str = typer.Option(..., "--symbol"),
    strategy: str = typer.Option("ma_crossover", "--strategy"),
    from_date: datetime = typer.Option(..., "--from", formats=["%Y-%m-%d"]),
    to_date: datetime = typer.Option(..., "--to", formats=["%Y-%m-%d"]),
    interval: int = typer.Option(0, "--interval", help="Bar minutes (0 = daily)"),
    fast: int = 20,
    slow: int = 50,
    capital: float = 1_000_000.0,
    risk_pct: float = 1.0,
    synthetic: bool = typer.Option(True, help="Use synthetic OHLC when Dhan creds not set"),
) -> None:
    settings = Settings()
    _setup_logging(settings)
    strat = _build_strategy(strategy, fast_period=fast, slow_period=slow)

    if synthetic or not settings.dhan_access_token:
        data_source = SyntheticMarketData()
        console.print("[yellow]Using synthetic market data.[/yellow]")
    else:
        from .dhan_client import DhanClient
        client = DhanClient(settings.dhan_client_id, settings.dhan_access_token)
        data_source = DhanMarketData(client)

    instrument = Instrument(symbol=symbol, exchange="NSE_EQ", security_id=f"STUB-{symbol}")
    result = run_backtest(
        strat, data_source, instrument, from_date.date(), to_date.date(),
        starting_cash=capital, risk_pct=risk_pct, interval_minutes=interval,
    )

    console.print(f"[bold]{result.summary()}[/bold]")
    if not result.trades:
        return
    tbl = Table(title=f"{symbol} trades")
    for col in ("Entry", "Exit", "Side", "Qty", "EntryPx", "ExitPx", "P&L", "Out"):
        tbl.add_column(col)
    for t in result.trades:
        tbl.add_row(
            str(t.entry_time)[:16], str(t.exit_time)[:16], t.side, str(t.qty),
            f"{t.entry:.2f}", f"{t.exit:.2f}", f"{t.pnl:+.2f}", t.reason_out,
        )
    console.print(tbl)


@app.command()
def run(
    dry: bool = typer.Option(False, "--dry"),
    i_understand_live_trading: bool = typer.Option(False, "--i-understand-live-trading"),
    config_path: str = "config/strategy.yaml",
) -> None:
    settings = Settings()
    _setup_logging(settings)
    cfg = load_strategy_config(config_path)
    strat = _build_strategy(cfg.strategy.name, **cfg.strategy.model_dump())
    instruments = _resolve_instruments(cfg)

    portfolio = Portfolio(settings.database_url, starting_cash=cfg.risk.starting_capital)
    guard = DailyLossGuard(cfg.risk.starting_capital, cfg.risk.daily_max_loss_pct)
    notifier = TelegramNotifier(
        bot_token=settings.telegram_bot_token, chat_id=settings.telegram_chat_id
    )
    if notifier.enabled:
        console.print("[green]Telegram notifications enabled.[/green]")

    if settings.execution_mode == ExecutionMode.LIVE:
        if not i_understand_live_trading:
            raise typer.BadParameter(
                "EXECUTION_MODE=live but --i-understand-live-trading not passed. Refusing to start."
            )
        from .dhan_client import DhanClient
        client = DhanClient(settings.dhan_client_id, settings.dhan_access_token)
        data_source = DhanMarketData(client)
        router = LiveExecutor(
            client=client,
            instruments={i.symbol: i for i in instruments},
            settings=settings,
            confirmed=True,
            notifier=notifier,
        )
        console.print("[bold red]LIVE MODE ENABLED - real orders will be placed.[/bold red]")
        notifier.alert(f"Bot starting in <b>LIVE</b> mode with {len(instruments)} symbols. Strategy={cfg.strategy.name}.")
    else:
        router = PaperExecutor(
            portfolio=portfolio, risk_pct=cfg.risk.per_trade_risk_pct, notifier=notifier
        )
        if settings.dhan_access_token:
            from .dhan_client import DhanClient
            client = DhanClient(settings.dhan_client_id, settings.dhan_access_token)
            data_source = DhanMarketData(client)
        else:
            data_source = SyntheticMarketData()
            console.print("[yellow]No Dhan creds set - using synthetic market data in paper mode.[/yellow]")
        notifier.send(f"📈 Paper bot started. Strategy=<b>{cfg.strategy.name}</b>, universe={cfg.universe}, symbols={len(instruments)}.")

    if dry:
        console.print(
            f"[green]Dry-run OK.[/green] strategy={cfg.strategy.name} mode={settings.execution_mode.value} "
            f"router={type(router).__name__} source={type(data_source).__name__} "
            f"universe={cfg.universe} symbols={len(instruments)} "
            f"capital={cfg.risk.starting_capital:,.0f} risk_pct={cfg.risk.per_trade_risk_pct} "
            f"daily_max_loss_pct={cfg.risk.daily_max_loss_pct}"
        )
        return

    from .scheduler import start_scheduler
    start_scheduler(strat, data_source, router, cfg, instruments, guard)


@app.command("test-telegram")
def test_telegram() -> None:
    """Send a test message via Telegram. Useful for verifying setup."""
    settings = Settings()
    n = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    if not n.enabled:
        console.print("[red]TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is empty in .env[/red]")
        raise typer.Exit(code=1)
    ok = n.send("✅ <b>Trading bot Telegram setup works!</b>\nYou will get a message here on every paper/live trade.")
    if ok:
        console.print("[green]Sent. Check your Telegram chat with the bot.[/green]")
    else:
        console.print("[red]Failed to send. Check token/chat_id and try again.[/red]")
        raise typer.Exit(code=1)


@app.command()
def status() -> None:
    settings = Settings()
    portfolio = Portfolio(settings.database_url, starting_cash=0)
    positions = portfolio.positions()
    if not positions:
        console.print("[dim]no open positions[/dim]")
        return
    tbl = Table(title="Open positions")
    tbl.add_column("Symbol"); tbl.add_column("Qty"); tbl.add_column("Avg price")
    for p in positions:
        tbl.add_row(p.symbol, str(p.qty), f"{p.avg_price:.2f}")
    console.print(tbl)


if __name__ == "__main__":
    app()
