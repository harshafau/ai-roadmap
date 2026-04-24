"""Thin wrapper around the official `dhanhq` Python SDK.

Only the calls we actually use are exposed. Import of `dhanhq` is lazy so that
tests and mocked backtests can run without the SDK installed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

import pandas as pd


@dataclass(frozen=True)
class Instrument:
    symbol: str
    exchange: str
    security_id: str


class DhanSDK(Protocol):
    def historical_daily_data(self, *args: Any, **kwargs: Any) -> dict: ...
    def get_ltp(self, *args: Any, **kwargs: Any) -> dict: ...
    def place_order(self, *args: Any, **kwargs: Any) -> dict: ...


class DhanClient:
    def __init__(self, client_id: str, access_token: str, sdk: DhanSDK | None = None):
        self._client_id = client_id
        self._access_token = access_token
        self._sdk = sdk or self._build_sdk(client_id, access_token)

    @staticmethod
    def _build_sdk(client_id: str, access_token: str) -> DhanSDK:
        from dhanhq import dhanhq

        return dhanhq(client_id, access_token)

    def historical_daily(
        self,
        instrument: Instrument,
        from_date: date,
        to_date: date,
    ) -> pd.DataFrame:
        resp = self._sdk.historical_daily_data(
            security_id=instrument.security_id,
            exchange_segment=instrument.exchange,
            instrument_type="EQUITY",
            from_date=str(from_date),
            to_date=str(to_date),
        )
        data = resp.get("data") or resp
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(data["timestamp"], unit="s"),
                "open": data["open"],
                "high": data["high"],
                "low": data["low"],
                "close": data["close"],
                "volume": data["volume"],
            }
        ).set_index("date")
        return df

    def ltp(self, instrument: Instrument) -> float:
        resp = self._sdk.get_ltp(
            security_id=instrument.security_id,
            exchange_segment=instrument.exchange,
        )
        return float(resp["data"]["ltp"])
