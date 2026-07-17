from datetime import date

import pandas as pd
import pytest

from app.providers.market_data import BarResult
from app.services.report import build_symbol_report


class FakeMarketData:
    def __init__(self, bars: pd.DataFrame) -> None:
        self.bars = bars
        self.request: tuple[str, str, str] | None = None

    def daily_bars(self, symbol: str, start: str, end: str) -> BarResult:
        self.request = (symbol, start, end)
        return BarResult(symbol=symbol, bars=self.bars)


class NoAI:
    def generate(self, facts: object) -> None:
        return None


def _bars() -> pd.DataFrame:
    index = pd.bdate_range("2025-01-02", periods=220)
    close = list(range(100, 320))
    return pd.DataFrame(
        {
            "Open": [value - 0.5 for value in close],
            "High": [value + 1 for value in close],
            "Low": [value - 1 for value in close],
            "Close": close,
            "Volume": [1_000_000] * 220,
        },
        index=index,
    )


def test_report_uses_same_bounded_market_bars_for_chart_and_technical_context() -> None:
    market_data = FakeMarketData(_bars())

    report = build_symbol_report(
        "MU", market_data=market_data, ai_client=NoAI(), today=date(2025, 12, 31)
    )

    assert market_data.request == ("MU", "2023-01-01", "2026-01-01")
    assert len(report["chart_bars"]) == 220
    assert report["chart_bars"][0]["date"] == "2025-01-02"
    assert report["chart_bars"][-1]["close"] == report["technical_context"]["close"]
    assert report["chart_bars"][-1]["sma_50"] == report["technical_context"]["sma_50"]
    assert report["chart_bars"][-1]["sma_200"] == report["technical_context"]["sma_200"]


def test_report_rejects_invalid_ohlcv_chart_data() -> None:
    bars = _bars()
    bars.iloc[-1, bars.columns.get_loc("High")] = 1

    with pytest.raises(ValueError, match="chart bars require finite OHLCV values"):
        build_symbol_report("MU", market_data=FakeMarketData(bars), ai_client=NoAI())
