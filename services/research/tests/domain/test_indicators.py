import pandas as pd

from app.domain.indicators import build_technical_context


def test_context_calculates_daily_trend_momentum_and_volatility_features() -> None:
    closes = list(range(1, 221))
    frame = pd.DataFrame(
        {
            "Close": closes,
            "High": closes,
            "Low": closes,
            "Volume": [100] * 220,
        }
    )

    context = build_technical_context(frame)

    assert context.close == 220.0
    assert context.sma_50 == 195.5
    assert context.sma_200 == 120.5
    assert context.rsi_14 == 100.0
    assert context.atr_14 == 1.0
    assert context.distance_from_20d_high == 0.0
    assert context.average_volume_20 == 100.0


def test_context_rejects_insufficient_daily_history() -> None:
    frame = pd.DataFrame(
        {
            "Close": [1] * 199,
            "High": [1] * 199,
            "Low": [1] * 199,
            "Volume": [1] * 199,
        }
    )

    try:
        build_technical_context(frame)
    except ValueError as error:
        assert str(error) == "at least 200 daily bars are required"
    else:
        raise AssertionError("expected insufficient-history error")
