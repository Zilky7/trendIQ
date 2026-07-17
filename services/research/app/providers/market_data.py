from dataclasses import dataclass
from typing import Callable

import pandas as pd
import yfinance as yf

from app.services.bar_cache import BarCache


SOURCE_LABEL = "yfinance historical prototype data"
_REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


@dataclass(frozen=True)
class BarResult:
    symbol: str
    bars: pd.DataFrame
    source_label: str = SOURCE_LABEL


class YFinanceMarketDataProvider:
    def __init__(
        self,
        download: Callable[..., pd.DataFrame] = yf.download,
        cache: BarCache | None = None,
    ) -> None:
        self.download = download
        self.cache = cache or BarCache()

    def daily_bars(self, symbol: str, start: str, end: str) -> BarResult:
        normalized_symbol = symbol.upper()
        cached = self.cache.get(normalized_symbol, start, end)
        if cached is not None:
            return BarResult(symbol=normalized_symbol, bars=cached)

        raw = self.download(
            tickers=normalized_symbol,
            start=start,
            end=end,
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
        bars = _normalize_daily_bars(raw)
        if bars.empty:
            raise ValueError(f"no daily bars returned for {normalized_symbol}")

        self.cache.put(normalized_symbol, start, end, bars)
        return BarResult(symbol=normalized_symbol, bars=bars)


def _normalize_daily_bars(raw: pd.DataFrame) -> pd.DataFrame:
    bars = raw.copy()
    if isinstance(bars.columns, pd.MultiIndex):
        bars.columns = _price_columns_from_multiindex(bars.columns)

    bars = bars.rename(columns=lambda column: str(column).strip().title())
    missing = set(_REQUIRED_COLUMNS).difference(bars.columns)
    if missing:
        missing_names = ", ".join(sorted(missing))
        raise ValueError(f"daily bars missing required columns: {missing_names}")

    return bars.loc[:, _REQUIRED_COLUMNS].dropna().sort_index()


def _price_columns_from_multiindex(columns: pd.MultiIndex) -> pd.Index:
    required = set(_REQUIRED_COLUMNS)
    for level in range(columns.nlevels):
        flattened = pd.Index(columns.get_level_values(level))
        titled = flattened.map(lambda column: str(column).strip().title())
        if required.issubset(set(titled)):
            return titled
    raise ValueError("daily bars multi-index is missing a price-column level")
