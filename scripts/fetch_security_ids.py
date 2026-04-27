"""Resolve Dhan `security_id` for each symbol in a universe CSV.

Usage:
    python scripts/fetch_security_ids.py config/universe/nifty50.csv

Downloads Dhan's public instrument master, joins on tradingsymbol + exchange,
writes the result back to the same CSV. Run once per universe whenever Dhan
rotates IDs (rare).

Requires `requests` and Dhan credentials are NOT needed (the master CSV is
publicly served by Dhan).
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

import requests

DHAN_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"


def main(path: str) -> int:
    p = Path(path)
    if not p.exists():
        print(f"missing {p}", file=sys.stderr)
        return 1

    print(f"fetching {DHAN_MASTER_URL}")
    resp = requests.get(DHAN_MASTER_URL, timeout=60)
    resp.raise_for_status()
    master = list(csv.DictReader(io.StringIO(resp.text)))
    # Index by (tradingsymbol, segment) for NSE Equity rows.
    by_key: dict[tuple[str, str], str] = {}
    for row in master:
        seg = row.get("SEM_EXM_EXCH_ID", "")
        instr = row.get("SEM_INSTRUMENT_NAME", "")
        if seg == "NSE" and instr == "EQUITY":
            key = (row["SEM_TRADING_SYMBOL"].split("-")[0], "NSE_EQ")
            by_key[key] = row["SEM_SMST_SECURITY_ID"]

    with p.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        fields = reader.fieldnames or ["symbol", "exchange", "security_id"]

    resolved = 0
    for r in rows:
        sym = (r.get("symbol") or "").strip()
        exch = (r.get("exchange") or "NSE_EQ").strip()
        sid = by_key.get((sym, exch))
        if sid:
            r["security_id"] = sid
            resolved += 1
        elif not r.get("security_id"):
            r["security_id"] = ""

    with p.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"resolved {resolved}/{len(rows)} security_ids in {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "config/universe/nifty50.csv"))
