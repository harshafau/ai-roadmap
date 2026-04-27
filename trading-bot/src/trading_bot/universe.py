"""Universe loader.

Reads a CSV of {symbol, exchange, security_id} and produces a list of
`Instrument`. The `security_id` column may be empty until populated from Dhan's
instrument-master CSV (see scripts/fetch_security_ids.py). When empty, a
deterministic STUB id is used so paper-mode + synthetic data still work.
"""
from __future__ import annotations

import csv
from pathlib import Path

from .dhan_client import Instrument


def load_universe(path: str | Path) -> list[Instrument]:
    instruments: list[Instrument] = []
    with open(path, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            symbol = (row.get("symbol") or "").strip()
            if not symbol:
                continue
            exchange = (row.get("exchange") or "NSE_EQ").strip()
            sid = (row.get("security_id") or "").strip() or f"STUB-{symbol}"
            instruments.append(Instrument(symbol=symbol, exchange=exchange, security_id=sid))
    return instruments


def universe_path(name: str) -> Path:
    """`name` like 'nifty50', 'nifty100', 'nifty500'."""
    return Path("config") / "universe" / f"{name}.csv"
