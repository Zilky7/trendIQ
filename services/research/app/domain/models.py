from dataclasses import dataclass


@dataclass(frozen=True)
class TechnicalContext:
    close: float
    sma_50: float
    sma_200: float
    rsi_14: float
    atr_14: float
    distance_from_20d_high: float
    average_volume_20: float
