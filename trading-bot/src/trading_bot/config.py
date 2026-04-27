from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutionMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    dhan_client_id: str = ""
    dhan_access_token: str = ""
    execution_mode: ExecutionMode = ExecutionMode.PAPER
    database_url: str = "sqlite:///trading.db"
    log_level: str = "INFO"

    # Optional: set both to receive Telegram push notifications on every trade
    # plus a daily P&L summary. Leave empty to disable (no errors).
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


class WatchlistItem(BaseModel):
    symbol: str
    exchange: str = "NSE_EQ"


class StrategyParams(BaseModel):
    model_config = {"extra": "allow"}  # accept arbitrary per-strategy params
    name: str
    fast_period: int = 20
    slow_period: int = 50


class RiskParams(BaseModel):
    starting_capital: float = Field(gt=0)
    per_trade_risk_pct: float = Field(gt=0, le=100)
    max_open_positions: int = Field(gt=0)
    daily_max_loss_pct: float = Field(default=3.0, gt=0, le=100)


class ScheduleParams(BaseModel):
    cron: str
    timezone: str = "Asia/Kolkata"
    bar_interval_minutes: int = 5


class StrategyConfig(BaseModel):
    strategy: StrategyParams
    risk: RiskParams
    schedule: ScheduleParams
    # Either a universe name (loaded from config/universe/<name>.csv) or an
    # inline watchlist for ad-hoc setups.
    universe: str | None = None
    watchlist: List[WatchlistItem] | None = None


def load_strategy_config(path: str | Path = "config/strategy.yaml") -> StrategyConfig:
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return StrategyConfig(**raw)
