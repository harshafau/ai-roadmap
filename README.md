# Trading Bot (DhanHQ, paper-first)

A Python service that runs automated trading strategies against DhanHQ (Indian
broker API). Paper-trading is the default and only mode enabled out of the box;
live order placement requires two explicit opt-ins.

> **This folder lives inside the `ai-roadmap` repo only because of tooling
> scope.** It is fully self-contained and has no dependency on the static site.
> See [Moving to its own repo](#moving-to-its-own-repo) below.

## Status

- Strategy: **Moving-average crossover** (fast/slow SMA).
- Market data: DhanHQ daily OHLC (or synthetic for dev without credentials).
- Execution: **paper** (SQLite ledger). Live path exists but is gated off.
- Schedule: daily post-close (15:25 IST) via APScheduler.

## Safety model

Two independent gates must both open for a real order to hit Dhan:

1. `EXECUTION_MODE=live` in `.env`.
2. CLI flag `--i-understand-live-trading` on `trading-bot run`.

If either is missing, `LiveExecutor.route()` raises `RuntimeError`. Default
`.env.example` ships with `EXECUTION_MODE=paper`.

## Install

Requires Python 3.11+.

```bash
cd trading-bot
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Getting Dhan API credentials

1. Log in at <https://web.dhan.co>.
2. Top-right menu → **My Profile** → **DhanHQ Trading APIs** → **Access DhanHQ APIs**.
3. Click **Generate Access Token**. Pick the validity (24h / long-lived).
4. Copy your **Client ID** from the same panel and the **Access Token** you just
   generated.
5. `cp .env.example .env` and paste both values. Do **not** commit `.env`.

> Dhan will show an algo-trading/API usage acknowledgement the first time you
> enable it. Read it — SEBI rules on retail algo trading apply.

## Run

```bash
# 1. Quick sanity check (no creds needed, uses synthetic data).
trading-bot backtest --symbol RELIANCE --from 2023-01-01 --to 2024-12-31

# 2. Wire everything but don't start the scheduler. Confirms config + mode.
trading-bot run --dry

# 3. Start the paper-trading scheduler. Blocks until Ctrl-C.
trading-bot run

# 4. Inspect the paper ledger.
trading-bot status
```

## Going live (later, not now)

Only do this after several weeks of paper-trading and inspection of
`trading.db`:

```bash
# 1. Set EXECUTION_MODE=live in .env
# 2. Pass the explicit confirm flag:
trading-bot run --i-understand-live-trading
```

## Layout

```
src/trading_bot/
    config.py           # Settings (env) + StrategyConfig (YAML)
    dhan_client.py      # DhanHQ SDK wrapper
    market_data.py      # DhanMarketData + SyntheticMarketData
    strategy/
        base.py         # Strategy ABC, Signal
        ma_crossover.py # MA crossover implementation
    portfolio.py        # SQLAlchemy ledger
    executor/
        paper.py        # simulated fills
        live.py         # real orders, gated off
    backtest.py         # walk-forward backtest
    scheduler.py        # APScheduler wiring
    cli.py              # Typer entrypoints
config/strategy.yaml    # watchlist, periods, risk
tests/                  # pytest suite
```

## Adding another strategy

1. Create `src/trading_bot/strategy/my_strategy.py` subclassing `Strategy`.
2. Implement `generate_signal(self, symbol, bars) -> Signal`.
3. Export it from `strategy/__init__.py`.
4. Add tests in `tests/test_my_strategy.py`.
5. Wire selection via config (`config/strategy.yaml: strategy.name`).

## Moving to its own repo

When you want to promote this to a standalone repo:

```bash
# From the ai-roadmap repo root
git subtree split --prefix=trading-bot -b trading-bot-export
mkdir ../trading-bot-standalone && cd ../trading-bot-standalone
git init && git pull ../ai-roadmap trading-bot-export
git remote add origin git@github.com:<you>/trading-bot.git
git push -u origin main
```

Then delete `trading-bot/` from `ai-roadmap` in a follow-up commit.

## Disclaimers

This is **educational software**. No warranty of profitability, suitability,
or regulatory compliance. Automated trading on Indian markets is subject to
SEBI regulations and Dhan's terms of service — your account, your
responsibility.
