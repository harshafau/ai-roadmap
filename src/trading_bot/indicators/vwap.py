from __future__ import annotations

import pandas as pd


def session_vwap(bars: pd.DataFrame) -> pd.Series:
    """Anchored VWAP that resets each calendar day.

    typical_price = (high + low + close) / 3
    vwap_t = cumsum(tp * vol) / cumsum(vol), reset per session.

    Bars index must be a DatetimeIndex.
    """
    if not isinstance(bars.index, pd.DatetimeIndex):
        raise TypeError("session_vwap requires a DatetimeIndex")
    tp = (bars["high"] + bars["low"] + bars["close"]) / 3.0
    pv = tp * bars["volume"]
    session_key = bars.index.normalize()
    cum_pv = pv.groupby(session_key).cumsum()
    cum_v = bars["volume"].groupby(session_key).cumsum()
    return (cum_pv / cum_v).rename("vwap")
