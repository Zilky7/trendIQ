from app.domain.strategy import ResearchWindow, StrategyFeatures, determine_signal


def test_research_window_allows_parameter_selection_through_2024_only() -> None:
    window = ResearchWindow()

    assert window.development_end == "2024-12-31"
    assert window.validation_start == "2025-01-01"
    assert window.can_select_parameters("2024-12-31") is True
    assert window.can_select_parameters("2025-01-01") is False


def test_strategy_signal_is_long_for_a_bullish_non_overbought_breakout() -> None:
    features = StrategyFeatures(
        close=105,
        sma_50=100,
        sma_200=90,
        rsi_14=62,
        distance_from_20d_high=-1,
        atr_14=2,
        volume_ratio=1.4,
    )

    signal = determine_signal(features)

    assert signal.side == "long"
    assert signal.reason == "bullish_trend_breakout"
