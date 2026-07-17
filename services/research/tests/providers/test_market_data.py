import pandas as pd
import pytest

from app.providers.market_data import NasdaqHistoricalDataProvider, YFinanceMarketDataProvider
from app.services.bar_cache import BarCache


SOURCE_LABEL = "yfinance historical prototype data"


def raw_daily_bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [10.0],
            "High": [12.0],
            "Low": [9.0],
            "Close": [11.0],
            "Volume": [50],
        },
        index=pd.to_datetime(["2024-01-02"]),
    )


def test_provider_normalizes_adjusted_daily_ohlcv_and_marks_yfinance_source(tmp_path) -> None:
    provider = YFinanceMarketDataProvider(
        download=lambda **_: raw_daily_bars(), cache=BarCache(cache_dir=tmp_path)
    )

    result = provider.daily_bars("mu", "2024-01-01", "2024-01-03")

    assert result.symbol == "MU"
    assert result.source_label == SOURCE_LABEL
    assert result.bars.columns.tolist() == ["Open", "High", "Low", "Close", "Volume"]
    assert result.bars.iloc[0].Close == 11.0


def test_provider_normalizes_single_symbol_yfinance_multiindex_columns(tmp_path) -> None:
    raw = raw_daily_bars()
    raw.columns = pd.MultiIndex.from_product([raw.columns, ["MU"]])
    provider = YFinanceMarketDataProvider(
        download=lambda **_: raw, cache=BarCache(cache_dir=tmp_path)
    )

    result = provider.daily_bars("MU", "2024-01-01", "2024-01-03")

    assert result.bars.columns.tolist() == ["Open", "High", "Low", "Close", "Volume"]
    assert result.bars.iloc[0].Close == 11.0


def test_provider_reuses_only_a_cache_interval_that_fully_covers_request(tmp_path) -> None:
    calls = []

    def download(**kwargs):
        calls.append(kwargs)
        return raw_daily_bars()

    provider = YFinanceMarketDataProvider(
        download=download, cache=BarCache(cache_dir=tmp_path)
    )

    provider.daily_bars("MU", "2024-01-02", "2024-01-10")
    cached = provider.daily_bars("MU", "2024-01-02", "2024-01-03")
    provider.daily_bars("MU", "2024-01-01", "2024-01-11")

    assert len(calls) == 2
    assert cached.source_label == SOURCE_LABEL
    pd.testing.assert_frame_equal(cached.bars, raw_daily_bars())
    assert sorted(path.name for path in tmp_path.glob("*.parquet")) == [
        "MU__2024-01-01__2024-01-11.parquet",
        "MU__2024-01-02__2024-01-10.parquet",
    ]


def test_provider_trims_a_covering_cached_interval_to_the_requested_dates(tmp_path) -> None:
    raw = pd.DataFrame(
        {
            "Open": [10.0, 11.0, 12.0, 13.0],
            "High": [11.0, 12.0, 13.0, 14.0],
            "Low": [9.0, 10.0, 11.0, 12.0],
            "Close": [10.5, 11.5, 12.5, 13.5],
            "Volume": [50, 51, 52, 53],
        },
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-08", "2024-01-09"]),
    )
    provider = YFinanceMarketDataProvider(
        download=lambda **_: raw, cache=BarCache(cache_dir=tmp_path)
    )

    provider.daily_bars("MU", "2024-01-02", "2024-01-10")
    result = provider.daily_bars("MU", "2024-01-03", "2024-01-09")

    assert result.bars.index.tolist() == pd.to_datetime(["2024-01-03", "2024-01-08"]).tolist()


def test_provider_trims_fresh_download_before_returning_and_caching(tmp_path) -> None:
    raw = pd.DataFrame(
        {
            "Open": [10.0, 11.0, 12.0, 13.0, 14.0],
            "High": [11.0, 12.0, 13.0, 14.0, 15.0],
            "Low": [9.0, 10.0, 11.0, 12.0, 13.0],
            "Close": [10.5, 11.5, 12.5, 13.5, 14.5],
            "Volume": [50, 51, 52, 53, 54],
        },
        index=pd.to_datetime(
            ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
        ),
    )
    provider = YFinanceMarketDataProvider(
        download=lambda **_: raw, cache=BarCache(cache_dir=tmp_path)
    )

    result = provider.daily_bars("MU", "2024-01-02", "2024-01-05")
    cached = pd.read_parquet(tmp_path / "MU__2024-01-02__2024-01-05.parquet")

    expected_dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]).tolist()
    assert result.bars.index.tolist() == expected_dates
    assert cached.index.tolist() == expected_dates


def test_nasdaq_provider_normalizes_reverse_order_daily_rows_and_marks_fallback_source(
    tmp_path,
) -> None:
    seen: dict[str, object] = {}

    def get_json(url: str, params: dict[str, str]) -> dict[str, object]:
        seen["url"] = url
        seen["params"] = params
        return {
            "data": {
                "tradesTable": {
                    "rows": [
                        {"date": "01/03/2025", "open": "$102.00", "high": "$104.00", "low": "$101.00", "close": "$103.00", "volume": "1,200"},
                        {"date": "01/02/2025", "open": "$100.00", "high": "$103.00", "low": "$99.00", "close": "$102.00", "volume": "1,000"},
                    ]
                }
            }
        }

    provider = NasdaqHistoricalDataProvider(get_json=get_json, cache=BarCache(cache_dir=tmp_path))
    result = provider.daily_bars("mu", "2025-01-01", "2025-01-04")

    assert seen["params"] == {
        "assetclass": "stocks",
        "fromdate": "2025-01-01",
        "todate": "2025-01-04",
        "limit": "5000",
    }
    assert result.source_label == "Nasdaq historical daily fallback data (unadjusted)"
    assert result.bars.index.tolist() == pd.to_datetime(["2025-01-02", "2025-01-03"]).tolist()
    assert result.bars.iloc[-1].Close == 103.0


def test_nasdaq_provider_rejects_an_empty_or_malformed_response(tmp_path) -> None:
    provider = NasdaqHistoricalDataProvider(
        get_json=lambda *_: {"data": {"tradesTable": {"rows": []}}},
        cache=BarCache(cache_dir=tmp_path),
    )

    with pytest.raises(ValueError, match="no daily bars returned for MU"):
        provider.daily_bars("MU", "2025-01-01", "2025-01-04")
