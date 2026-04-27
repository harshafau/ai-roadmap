# Trading Bot (DhanHQ, paper-first)

A Python service that runs automated trading strategies against DhanHQ (Indian
broker API). Paper-trading is the default; live order placement requires two
explicit opt-ins. Built for a ₹10 lakh capital base with 1% per-trade risk.

> This folder lives inside the `ai-roadmap` repo only because of tooling
> scope. It is fully self-contained — see [Moving to its own repo](#moving-to-its-own-repo).

## Do you need TradingView?

**No.** Dhan's REST + WebSocket APIs cover everything: historical OHLCV (daily
+ intraday), live LTP and 5-level market depth, and order placement. People add
TradingView only as a charting/PineScript-prototyping layer; we don't.

If you ever want it, the integration shape is: TV alert → webhook → small Flask
endpoint → router. We have not built it. It's optional and adds a TV Pro+
subscription cost.

## Strategies shipped

| Name | Bars | Idea |
|---|---|---|
| `ma_crossover` | daily | Fast/slow SMA crossover (sanity baseline) |
| `sweep_vwap_reclaim` | 5-min | Liquidity sweep of recent swing high/low + VWAP reclaim. Confluence: ATR/RSI + order-flow proxy (volume delta + 5-level book imbalance). |
| `volume_profile_poc_vwap` | 5-min | Mean-reversion at session VAH/VAL with VWAP + RSI exhaustion filters; target POC. |
| `ema_fvg_vwap` | 5-min | 50-EMA + VWAP trend filter; entries on retest of unfilled fair-value gap aligned with the trend. |

Switch the active strategy in `config/strategy.yaml` (`strategy.name`) or via
`trading-bot list-strategies` / `trading-bot backtest --strategy ...`.

### Honest limitations

- **"Order flow" is a proxy, not institutional footprint.** True tick-level CVD
  needs per-trade aggressor classification which Dhan's retail API does not
  expose. The bot uses `volume_delta = sign(close-open) * volume` plus 5-level
  book imbalance from the depth WebSocket. Treat it as suggestive, not as
  Bookmap-grade order flow.
- **These strategies are unproven for your context.** Don't infer profitability
  from internet hype or the synthetic-data smoke metrics in this repo (random
  walks → results are noise). You **must** paper-trade them for at least a
  month and review win-rate/expectancy/drawdown before considering live.
- **5-level depth ≠ full book.** NSE publishes 20 levels publicly; Dhan WS
  exposes 5. Imbalance signal is therefore shallow.

## Safety model

Two independent gates must both open for a real order to hit Dhan:

1. `EXECUTION_MODE=live` in `.env`.
2. CLI flag `--i-understand-live-trading` on `trading-bot run`.

If either is missing, `LiveExecutor.route()` raises `RuntimeError`. Default
`.env.example` ships with `EXECUTION_MODE=paper`.

The scheduler also enforces a **daily-loss guard**: realized P&L below
`risk.daily_max_loss_pct` (default 3% = ₹30,000) stops trading for the rest of
the session.

## Mobile access (iPhone or Android)

Three independent surfaces; pick what you need:

1. **GitHub mobile app** — view code, commits, branches. Free, no setup
   beyond installing the app and logging in to your GitHub account.
2. **Telegram bot** (built in) — push notifications on every paper/live
   trade with symbol, qty, stop, target, and the strategy reason. Works
   anywhere you have Telegram. Setup steps in `.env.example`. Verify with
   `trading-bot test-telegram`.
3. **Dhan mobile app** — once you go live, real positions and P&L appear
   in Dhan's official app like any manual trade. Paper-mode trades do NOT
   appear in Dhan because they're never sent.

Telegram is opt-in: leave the env vars empty and the bot runs silently
without errors.

## Risk framework

- Capital: configurable, default ₹10,00,000 (ten lakh).
- Per-trade risk: 1% (₹10,000) — position size derived from stop distance.
- Max concurrent positions: 3.
- Daily max loss: 3% — bot pauses until next session.

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
4. Copy your **Client ID** and the **Access Token**.
5. `cp .env.example .env`, paste both values. Do **not** commit `.env`.
6. Run `python scripts/fetch_security_ids.py config/universe/nifty50.csv` once
   to populate Dhan `security_id`s for the watchlist (the public Dhan
   instrument-master CSV is used; no auth required).

> Dhan will show an algo-trading/API usage acknowledgement the first time you
> enable it. SEBI rules on retail algo trading apply — read it.

## Run

```bash
# Catalogue of strategies.
trading-bot list-strategies

# Synthetic-data smoke (no Dhan creds needed) — verifies the pipeline runs.
trading-bot backtest --strategy sweep_vwap_reclaim \
    --symbol RELIANCE --from 2024-01-01 --to 2024-12-31 --interval 5

# Wire everything but don't start the scheduler.
trading-bot run --dry

# Start the paper-trading scheduler. Blocks until Ctrl-C.
trading-bot run

# Inspect the paper ledger.
trading-bot status
```

## Universe

Watchlist comes from `config/universe/<name>.csv`. Shipped:

- `config/universe/nifty50.csv` — symbols only; run the fetcher to fill IDs.

To run on Nifty 100 / 500: download the constituent CSV from NSE
(<https://www.nseindia.com/market-data/live-equity-market>), drop it at
`config/universe/nifty500.csv` with columns `symbol,exchange,security_id` (the
ID column may be empty), then run `scripts/fetch_security_ids.py` against it.
Set `universe: nifty500` in `config/strategy.yaml`.

## Going live (later, not now)

Only after a full month of paper trading and review of `trading.db`:

```bash
# 1. Set EXECUTION_MODE=live in .env
# 2. Pass the explicit confirm flag:
trading-bot run --i-understand-live-trading
```

## Layout

```
src/trading_bot/
    config.py
    dhan_client.py            # SDK wrapper (daily + intraday + LTP + orders)
    market_data.py            # DhanMarketData + SyntheticMarketData
    indicators/               # vwap, ema, rsi, atr, swing, volume_profile, volume_delta, book_imbalance
    patterns/                 # liquidity_sweep, fair_value_gap
    strategy/                 # ma_crossover + 3 composite strategies
    portfolio.py              # SQLAlchemy ledger
    executor/paper.py         # simulated fills with risk-based sizing
    executor/live.py          # real orders, gated off
    risk.py                   # position_size + DailyLossGuard
    backtest.py               # walk-forward + metrics (win rate, expectancy, drawdown, sharpe)
    scheduler.py              # APScheduler intraday/daily
    universe.py               # CSV → list[Instrument]
    cli.py                    # Typer entrypoints
config/strategy.yaml          # active strategy + universe + risk + schedule
config/universe/nifty50.csv   # symbols, IDs filled by scripts/fetch_security_ids.py
scripts/fetch_security_ids.py # joins watchlist with Dhan instrument master
tests/                        # 34 tests, all offline
```

## Adding another strategy

1. Create `src/trading_bot/strategy/my_strategy.py` subclassing `Strategy`.
2. Implement `generate_signal(self, symbol, bars, context=None) -> Signal`.
   Return `Signal` with `stop_loss` and `take_profit` so the risk-sizer can
   compute qty.
3. Register in `STRATEGIES` (in `strategy/__init__.py`).
4. Add tests; switch `strategy.name` in YAML.

## Moving to its own repo

```bash
# From the ai-roadmap repo root
git subtree split --prefix=trading-bot -b trading-bot-export
mkdir ../trading-bot-standalone && cd ../trading-bot-standalone
git init && git pull ../ai-roadmap trading-bot-export
git remote add origin git@github.com:<you>/trading-bot.git
git push -u origin main
```

## Disclaimers

This is **educational software**. No warranty of profitability, suitability,
or regulatory compliance. Automated trading on Indian markets is subject to
SEBI regulations and Dhan's terms of service. **Your account, your risk.**
Never deploy strategies to live without a thorough out-of-sample validation
period.
