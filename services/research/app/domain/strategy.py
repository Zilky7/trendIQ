"""Pure strategy contracts and the fixed research-window boundary."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchWindow:
    development_start: str = "2020-01-01"
    development_end: str = "2024-12-31"
    validation_start: str = "2025-01-01"
    validation_end: str = "2025-12-31"

    def can_select_parameters(self, date: str) -> bool:
        """Return whether a date belongs to the parameter-development period."""
        return self.development_start <= date <= self.development_end


@dataclass(frozen=True)
class StrategyFeatures:
    close: float
    sma_50: float
    sma_200: float
    rsi_14: float
    distance_from_20d_high: float
    atr_14: float
    volume_ratio: float


@dataclass(frozen=True)
class StrategySignal:
    """Stable, serializable outcome of evaluating the first strategy rule."""

    side: str
    reason: str


def determine_signal(features: StrategyFeatures) -> StrategySignal:
    is_bullish_breakout = (
        features.close > features.sma_50 > features.sma_200
        and 50 <= features.rsi_14 < 70
        and features.distance_from_20d_high >= -3
        and features.volume_ratio >= 1
    )
    if is_bullish_breakout:
        return StrategySignal(side="long", reason="bullish_trend_breakout")
    return StrategySignal(side="neutral", reason="conditions_not_met")
