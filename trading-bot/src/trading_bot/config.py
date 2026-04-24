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


class WatchlistItem(BaseModel):
    symbol: str
    exchange: str = "NSE_EQ"


class StrategyParams(BaseModel):
    name: str
    fast_period: int = Field(gt=0)
    slow_period: int = Field(gt=0)


class RiskParams(BaseModel):
    starting_capital: float = Field(gt=0)
    per_trade_risk_pct: float = Field(gt=0, le=100)
    max_open_positions: int = Field(gt=0)


class ScheduleParams(BaseModel):
    cron: str
    timezone: str = "Asia/Kolkata"


class StrategyConfig(BaseModel):
    strategy: StrategyParams
    watchlist: List[WatchlistItem]
    risk: RiskParams
    schedule: ScheduleParams


def load_strategy_config(path: str | Path = "config/strategy.yaml") -> StrategyConfig:
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return StrategyConfig(**raw)
