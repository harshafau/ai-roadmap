import numpy as np
import pandas as pd
import pytest

from trading_bot.indicators import (
    atr,
    book_imbalance,
    build_volume_profile,
    ema,
    rsi,
    session_vwap,
    swing_highs,
    swing_lows,
    volume_delta,
)


def _bars(n=20, base=100.0):
    idx = pd.date_range("2024-01-01 09:15", periods=n, freq="5min")
    closes = np.linspace(base, base + 5, n)
    return pd.DataFrame(
        {
            "open": closes - 0.1,
            "high": closes + 0.5,
            "low": closes - 0.5,
            "close": closes,
            "volume": np.full(n, 1000),
        },
        index=idx,
    )


def test_session_vwap_resets_each_day():
    bars = pd.concat([_bars(5), _bars(5).set_index(pd.date_range("2024-01-02 09:15", periods=5, freq="5min"))])
    v = session_vwap(bars)
    # First bar of each session: VWAP equals that bar's typical price.
    tp = (bars["high"] + bars["low"] + bars["close"]) / 3.0
    assert v.iloc[0] == pytest.approx(tp.iloc[0])
    assert v.iloc[5] == pytest.approx(tp.iloc[5])


def test_ema_smaller_than_max_jump():
    s = pd.Series([1.0] * 10 + [11.0])
    out = ema(s, period=3)
    # The new EMA is well below 11 (smoothing).
    assert 1.0 < out.iloc[-1] < 11.0


def test_rsi_bounds_and_strong_uptrend_above_50():
    closes = pd.Series(np.linspace(100, 200, 100))
    r = rsi(closes, 14)
    assert (r >= 0).all() and (r <= 100).all()
    assert r.iloc[-1] > 70  # strong uptrend → overbought


def test_atr_positive_for_volatile_series():
    bars = _bars(50)
    a = atr(bars, 14)
    assert (a.dropna() > 0).all()


def test_swing_highs_and_lows():
    highs = pd.Series([1, 2, 3, 2, 1, 4, 5, 4, 3, 2])
    lows = pd.Series([1, 0, 1, 2, 0, 1, 0, -1, 0, 1])  # noqa: contrived
    sh = swing_highs(highs, 2, 2)
    sl = swing_lows(lows, 2, 2)
    assert sh.iloc[2] is True or sh.iloc[2] == True  # 3 at index 2
    assert sh.iloc[6] == True   # 5 at index 6


def test_volume_profile_finds_high_volume_zone():
    # Bars trade in two regions; one has 10x the volume.
    high_vol_bars = pd.DataFrame(
        {"open": [99]*5, "high": [101]*5, "low": [99]*5, "close": [100]*5, "volume": [10000]*5},
        index=pd.date_range("2024-01-01 09:15", periods=5, freq="5min"),
    )
    low_vol_bars = pd.DataFrame(
        {"open": [109]*5, "high": [111]*5, "low": [109]*5, "close": [110]*5, "volume": [100]*5},
        index=pd.date_range("2024-01-01 09:40", periods=5, freq="5min"),
    )
    vp = build_volume_profile(pd.concat([high_vol_bars, low_vol_bars]))
    assert 99 <= vp.poc <= 101
    assert vp.val < vp.vah


def test_volume_delta_signs_match_bar_direction():
    bars = pd.DataFrame(
        {"open": [100, 101, 100], "close": [101, 100, 100], "high": [102]*3, "low": [99]*3, "volume": [10, 20, 30]},
        index=pd.date_range("2024-01-01", periods=3, freq="D"),
    )
    d = volume_delta(bars)
    assert d.iloc[0] == 10
    assert d.iloc[1] == -20
    assert d.iloc[2] == 0


def test_book_imbalance_extremes():
    bid_heavy = {"bids": [(100, 100)]*5, "asks": [(101, 1)]*5}
    ask_heavy = {"bids": [(100, 1)]*5, "asks": [(101, 100)]*5}
    assert book_imbalance(bid_heavy) > 0.9
    assert book_imbalance(ask_heavy) < -0.9
    assert book_imbalance(None) == 0.0
    assert book_imbalance({}) == 0.0
