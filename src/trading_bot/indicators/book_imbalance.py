from __future__ import annotations

from typing import Iterable


def book_imbalance(book: dict | None, levels: int = 5) -> float:
    """Bid/ask depth imbalance from a Dhan 5-level snapshot.

    `book` is expected to look like:
        {"bids": [(price, qty), ...], "asks": [(price, qty), ...]}

    Returns a scalar in [-1, 1]:
        +1 fully bid-heavy, -1 fully ask-heavy, 0 balanced.
    Returns 0.0 if the snapshot is missing.
    """
    if not book:
        return 0.0
    bids: Iterable[tuple[float, int]] = book.get("bids", [])[:levels]
    asks: Iterable[tuple[float, int]] = book.get("asks", [])[:levels]
    bid_qty = sum(int(q) for _, q in bids)
    ask_qty = sum(int(q) for _, q in asks)
    total = bid_qty + ask_qty
    if total == 0:
        return 0.0
    return (bid_qty - ask_qty) / total
