import pandas as pd
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

from .models import TechnicalContext


def build_technical_context(bars: pd.DataFrame) -> TechnicalContext:
    if len(bars) < 200:
        raise ValueError("at least 200 daily bars are required")

    close = bars["Close"].astype(float)
    high = bars["High"].astype(float)
    low = bars["Low"].astype(float)
    latest = float(close.iloc[-1])
    high_20 = float(high.tail(20).max())

    return TechnicalContext(
        close=latest,
        sma_50=float(close.tail(50).mean()),
        sma_200=float(close.tail(200).mean()),
        rsi_14=round(float(RSIIndicator(close, window=14).rsi().iloc[-1]), 2),
        atr_14=round(
            float(
                AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1]
            ),
            4,
        ),
        distance_from_20d_high=round((latest / high_20 - 1) * 100, 2),
        average_volume_20=float(bars["Volume"].tail(20).mean()),
    )
