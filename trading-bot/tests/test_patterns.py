import numpy as np
import pandas as pd

from trading_bot.patterns import detect_fair_value_gaps, detect_liquidity_sweep, latest_unfilled_fvg


def _bar(o, h, l, c, v=1000):
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


def _df(rows):
    return pd.DataFrame(rows, index=pd.date_range("2024-01-01 09:15", periods=len(rows), freq="5min"))


def test_no_sweep_on_quiet_data():
    rows = [_bar(100, 101, 99, 100) for _ in range(30)]
    assert detect_liquidity_sweep(_df(rows)) is None


def test_bearish_sweep_detected():
    # Build a clear swing high around bar 10 at 110, then sweep above it on bar -1.
    rows = [_bar(100, 101, 99, 100) for _ in range(8)]
    rows += [_bar(105, 108, 104, 107)]
    rows += [_bar(108, 110, 107, 109)]   # swing high here at 110
    rows += [_bar(108, 109, 106, 107)]
    rows += [_bar(106, 107, 104, 105)]
    rows += [_bar(105, 106, 103, 104) for _ in range(8)]
    # Final bar: spike above 110 then close below it (bearish sweep + rejection).
    rows += [_bar(105, 112, 104, 108)]
    sweep = detect_liquidity_sweep(_df(rows))
    assert sweep is not None
    assert sweep.direction == "bearish"
    assert sweep.swept_level == 110
    assert sweep.sweep_extreme == 112


def test_bullish_sweep_detected():
    rows = [_bar(100, 101, 99, 100) for _ in range(8)]
    rows += [_bar(95, 96, 92, 93)]
    rows += [_bar(93, 94, 90, 91)]   # swing low here at 90
    rows += [_bar(92, 95, 91, 94)]
    rows += [_bar(95, 97, 94, 96)]
    rows += [_bar(96, 99, 95, 98) for _ in range(8)]
    rows += [_bar(98, 99, 88, 92)]   # wick below 90, close above
    sweep = detect_liquidity_sweep(_df(rows))
    assert sweep is not None
    assert sweep.direction == "bullish"
    assert sweep.swept_level == 90


def test_bullish_fvg_detected_and_filled():
    # Bar1 high=101, Bar2 jumps, Bar3 low=103 → bullish FVG [101,103]. Then a
    # later bar fills the mid (102).
    rows = [
        _bar(100, 101, 99, 100),
        _bar(101, 105, 101, 104),
        _bar(104, 106, 103, 105),
        _bar(105, 105, 102, 103),  # fills the FVG mid (102)
    ]
    gaps = detect_fair_value_gaps(_df(rows))
    bullish = [g for g in gaps if g.direction == "bullish"]
    assert len(bullish) == 1
    assert bullish[0].bottom == 101
    assert bullish[0].top == 103
    assert bullish[0].filled is True


def test_latest_unfilled_fvg_filters():
    rows = [
        _bar(100, 101, 99, 100),
        _bar(101, 105, 101, 104),
        _bar(104, 106, 103, 105),  # creates bullish FVG [101,103]
        _bar(105, 107, 105, 106),  # does NOT fill it (low 105 > 103)
    ]
    g = latest_unfilled_fvg(_df(rows), "bullish")
    assert g is not None
    assert g.filled is False
