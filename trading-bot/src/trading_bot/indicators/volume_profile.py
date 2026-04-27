from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VolumeProfile:
    """Discretised volume-by-price.

    `bins` are bin centres; `volumes[i]` is total traded volume in bin i.
    """
    bins: np.ndarray
    volumes: np.ndarray
    poc: float          # Point of Control: bin centre with max volume
    vah: float          # Value Area High (top of value_area_pct band)
    val: float          # Value Area Low

    def total_volume(self) -> float:
        return float(self.volumes.sum())


def build_volume_profile(
    bars: pd.DataFrame,
    bin_count: int = 30,
    value_area_pct: float = 0.70,
) -> VolumeProfile:
    """Distribute each bar's volume uniformly across [low, high] into price bins."""
    if bars.empty:
        return VolumeProfile(np.array([]), np.array([]), 0.0, 0.0, 0.0)

    lo = float(bars["low"].min())
    hi = float(bars["high"].max())
    if hi <= lo:
        return VolumeProfile(
            np.array([lo]), np.array([float(bars["volume"].sum())]), lo, lo, lo
        )

    edges = np.linspace(lo, hi, bin_count + 1)
    bin_centers = (edges[:-1] + edges[1:]) / 2.0
    bin_widths = edges[1:] - edges[:-1]
    volumes = np.zeros(bin_count)

    for low, high, vol in zip(bars["low"].to_numpy(), bars["high"].to_numpy(), bars["volume"].to_numpy()):
        if high <= low:
            idx = int(np.clip(np.searchsorted(edges, low) - 1, 0, bin_count - 1))
            volumes[idx] += vol
            continue
        # Distribute volume uniformly across the bar's range.
        left = np.clip(np.searchsorted(edges, low, side="right") - 1, 0, bin_count - 1)
        right = np.clip(np.searchsorted(edges, high, side="left"), 0, bin_count - 1)
        if right < left:
            right = left
        span = high - low
        for j in range(left, right + 1):
            overlap = min(high, edges[j + 1]) - max(low, edges[j])
            if overlap > 0:
                volumes[j] += vol * (overlap / span)

    poc_idx = int(np.argmax(volumes))
    poc = float(bin_centers[poc_idx])

    # Expand from POC outward until value_area_pct of total volume is captured.
    total = volumes.sum()
    target = total * value_area_pct
    captured = volumes[poc_idx]
    lo_idx = poc_idx
    hi_idx = poc_idx
    while captured < target and (lo_idx > 0 or hi_idx < bin_count - 1):
        next_lo = volumes[lo_idx - 1] if lo_idx > 0 else -1.0
        next_hi = volumes[hi_idx + 1] if hi_idx < bin_count - 1 else -1.0
        if next_hi >= next_lo:
            hi_idx = min(hi_idx + 1, bin_count - 1)
            captured += max(0.0, next_hi)
        else:
            lo_idx = max(lo_idx - 1, 0)
            captured += max(0.0, next_lo)

    val = float(edges[lo_idx])
    vah = float(edges[hi_idx + 1])
    return VolumeProfile(bin_centers, volumes, poc, vah, val)
