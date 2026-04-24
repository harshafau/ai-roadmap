"""Typer CLI.

Commands:
    trading-bot backtest --symbol RELIANCE --from 2024-01-01 --to 2024-12-31
    trading-bot run --dry
    trading-bot run --i-understand-live-trading
    trading-bot status
"""
from __future__ import annotations

import logging
from datetime import date, datetime

import typer
from rich.console import Console
from rich.table import Table

from .backtest import run_backtest
from .config import ExecutionMode, Settings, load_strategy_config
from .dhan_client import Instrument
from .executor import LiveExecutor, PaperExecutor
from .market_data import DhanMarketData, SyntheticMarketData
from .portfolio import Portfolio
from .strategy import MACrossoverStrategy

app = typer.Typer(add_completion=False, help="Paper-first Dhan trading bot")
console = Console()


def _setup_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def _build_instruments_stub(symbols: list[str]) -> dict[str, Instrument]:
    # Real security_id lookup requires Dhan's instrument master CSV. For paper
    # mode with the synthetic data source we fabricate stable placeholders.
    return {s: Instrument(symbol=s, exchange="NSE_EQ", security_id=f"STUB-{s}") for s in symbols}


@app.command()
def backtest(
    symbol: str = typer.Option(..., "--symbol"),
    from_date: datetime = typer.Option(..., "--from", formats=["%Y-%m-%d"]),
    to_date: datetime = typer.Option(..., "--to", formats=["%Y-%m-%d"]),
    fast: int = 20,
    slow: int = 50,
    synthetic: bool = typer.Option(True, help="Use synthetic OHLC when Dhan creds not set"),
) -> None:
    settings = Settings()
    _setup_logging(settings)
    strategy = MACrossoverStrategy(fast_period=fast, slow_period=slow)

    if synthetic or not settings.dhan_access_token:
        data_source = SyntheticMarketData()
        console.print("[yellow]Using synthetic market data (no Dhan creds or --synthetic).[/yellow]")
    else:
        from .dhan_client import DhanClient
        client = DhanClient(settings.dhan_client_id, settings.dhan_access_token)
        data_source = DhanMarketData(client)

    instrument = Instrument(symbol=symbol, exchange="NSE_EQ", security_id=f"STUB-{symbol}")
    result = run_backtest(strategy, data_source, instrument, from_date.date(), to_date.date())

    console.print(f"[bold]{result.summary()}[/bold]")
    tbl = Table(title=f"{symbol} trades")
    tbl.add_column("Date"); tbl.add_column("Side"); tbl.add_column("Qty"); tbl.add_column("Price")
    for t in result.trades:
        tbl.add_row(str(t["date"].date()), t["side"], str(t["qty"]), f"{t['price']:.2f}")
    console.print(tbl)


@app.command()
def run(
    dry: bool = typer.Option(False, "--dry", help="Wire everything up but do not start scheduler"),
    i_understand_live_trading: bool = typer.Option(False, "--i-understand-live-trading"),
    config_path: str = "config/strategy.yaml",
) -> None:
    settings = Settings()
    _setup_logging(settings)
    cfg = load_strategy_config(config_path)
    strategy = MACrossoverStrategy(fast_period=cfg.strategy.fast_period, slow_period=cfg.strategy.slow_period)

    symbols = [w.symbol for w in cfg.watchlist]
    instruments = _build_instruments_stub(symbols)

    if settings.execution_mode == ExecutionMode.LIVE:
        if not i_understand_live_trading:
            raise typer.BadParameter(
                "EXECUTION_MODE=live but --i-understand-live-trading not passed. Refusing to start."
            )
        from .dhan_client import DhanClient
        client = DhanClient(settings.dhan_client_id, settings.dhan_access_token)
        data_source = DhanMarketData(client)
        router = LiveExecutor(client=client, instruments=instruments, settings=settings, confirmed=True)
        console.print("[bold red]LIVE MODE ENABLED - real orders will be placed.[/bold red]")
    else:
        portfolio = Portfolio(settings.database_url, starting_cash=cfg.risk.starting_capital)
        router = PaperExecutor(portfolio=portfolio)
        if settings.dhan_access_token:
            from .dhan_client import DhanClient
            client = DhanClient(settings.dhan_client_id, settings.dhan_access_token)
            data_source = DhanMarketData(client)
        else:
            data_source = SyntheticMarketData()
            console.print("[yellow]No Dhan creds set - using synthetic market data in paper mode.[/yellow]")

    if dry:
        console.print(f"[green]Dry-run OK.[/green] mode={settings.execution_mode.value} "
                      f"router={type(router).__name__} source={type(data_source).__name__} "
                      f"symbols={symbols}")
        return

    from .scheduler import start_scheduler
    start_scheduler(strategy, data_source, router, cfg, instruments)


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
