from .base import Signal, SignalType, Strategy, StrategyContext
from .ma_crossover import MACrossoverStrategy
from .sweep_vwap_reclaim import SweepVwapReclaimStrategy
from .volume_profile_poc_vwap import VolumeProfilePocVwapStrategy
from .ema_fvg_vwap import EmaFvgVwapStrategy

STRATEGIES = {
    "ma_crossover": MACrossoverStrategy,
    "sweep_vwap_reclaim": SweepVwapReclaimStrategy,
    "volume_profile_poc_vwap": VolumeProfilePocVwapStrategy,
    "ema_fvg_vwap": EmaFvgVwapStrategy,
}

__all__ = [
    "Signal",
    "SignalType",
    "Strategy",
    "StrategyContext",
    "MACrossoverStrategy",
    "SweepVwapReclaimStrategy",
    "VolumeProfilePocVwapStrategy",
    "EmaFvgVwapStrategy",
    "STRATEGIES",
]
