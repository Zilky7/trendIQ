from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Callable
from urllib.parse import urlencode

import pandas as pd
import yfinance as yf

from app.services.bar_cache import BarCache


SOURCE_LABEL = "yfinance historical prototype data"
NASDAQ_SOURCE_LABEL = "Nasdaq historical daily fallback data (unadjusted)"
_REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]
_NASDAQ_API_HOST = "api.nasdaq.com"
_NASDAQ_API_IP = "23.14.205.160"


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
            bars = _bars_in_requested_interval(cached, start, end)
            if bars.empty:
                raise ValueError(f"no daily bars returned for {normalized_symbol}")
            return BarResult(symbol=normalized_symbol, bars=bars)

        raw = self.download(
            tickers=normalized_symbol,
            start=start,
            end=end,
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
        bars = _bars_in_requested_interval(_normalize_daily_bars(raw), start, end)
        if bars.empty:
            raise ValueError(f"no daily bars returned for {normalized_symbol}")

        self.cache.put(normalized_symbol, start, end, bars)
        return BarResult(symbol=normalized_symbol, bars=bars)


NasdaqJsonGetter = Callable[[str, dict[str, str]], dict[str, Any]]


class NasdaqHistoricalDataProvider:
    """Fetch daily OHLCV from Nasdaq when Yahoo is unavailable in this network.

    The WSL resolver in this development environment cannot resolve external
    HTTPS names. Curl's ``--resolve`` retains normal TLS hostname validation
    while directing this one public endpoint to a configurable IP address.
    """

    def __init__(
        self,
        get_json: NasdaqJsonGetter | None = None,
        cache: BarCache | None = None,
    ) -> None:
        self.get_json = get_json or _fetch_nasdaq_json
        self.cache = cache or BarCache(cache_dir=_nasdaq_cache_dir())

    def daily_bars(self, symbol: str, start: str, end: str) -> BarResult:
        normalized_symbol = symbol.upper()
        cached = self.cache.get(normalized_symbol, start, end)
        if cached is not None:
            bars = _bars_in_requested_interval(cached, start, end)
            if bars.empty:
                raise ValueError(f"no daily bars returned for {normalized_symbol}")
            return BarResult(
                symbol=normalized_symbol,
                bars=bars,
                source_label=NASDAQ_SOURCE_LABEL,
            )

        payload = self.get_json(
            normalized_symbol,
            {
                "assetclass": "stocks",
                "fromdate": start,
                "todate": end,
                "limit": "5000",
            },
        )
        bars = _bars_in_requested_interval(_normalize_nasdaq_rows(payload), start, end)
        if bars.empty:
            raise ValueError(f"no daily bars returned for {normalized_symbol}")
        self.cache.put(normalized_symbol, start, end, bars)
        return BarResult(
            symbol=normalized_symbol,
            bars=bars,
            source_label=NASDAQ_SOURCE_LABEL,
        )


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


def _fetch_nasdaq_json(symbol: str, params: dict[str, str]) -> dict[str, Any]:
    query = urlencode(params)
    url = f"https://{_NASDAQ_API_HOST}/api/quote/{symbol}/historical?{query}"
    endpoint_ip = os.getenv("NASDAQ_API_IP", _NASDAQ_API_IP)
    result = subprocess.run(
        [
            "curl",
            "--fail-with-body",
            "--silent",
            "--show-error",
            "--connect-timeout",
            "8",
            "--max-time",
            "20",
            "--resolve",
            f"{_NASDAQ_API_HOST}:443:{endpoint_ip}",
            "-H",
            "User-Agent: Mozilla/5.0",
            "-H",
            "Accept: application/json, text/plain, */*",
            url,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict):
        raise ValueError("Nasdaq historical response is not an object")
    return payload


def _normalize_nasdaq_rows(payload: dict[str, Any]) -> pd.DataFrame:
    try:
        rows = payload["data"]["tradesTable"]["rows"]
    except (KeyError, TypeError) as error:
        raise ValueError("Nasdaq historical response has no daily rows") from error
    if not isinstance(rows, list):
        raise ValueError("Nasdaq historical response has no daily rows")
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=_REQUIRED_COLUMNS, index=pd.DatetimeIndex([]))
    required = {"date", "open", "high", "low", "close", "volume"}
    if not required.issubset(frame.columns):
        raise ValueError("Nasdaq historical response has malformed daily rows")
    normalized = pd.DataFrame(
        {
            "Open": _nasdaq_number(frame["open"]).to_numpy(),
            "High": _nasdaq_number(frame["high"]).to_numpy(),
            "Low": _nasdaq_number(frame["low"]).to_numpy(),
            "Close": _nasdaq_number(frame["close"]).to_numpy(),
            "Volume": _nasdaq_number(frame["volume"]).to_numpy(),
        },
        index=pd.to_datetime(frame["date"], format="%m/%d/%Y", errors="coerce"),
    )
    return normalized.dropna().sort_index()


def _nasdaq_number(values: pd.Series) -> pd.Series:
    return pd.to_numeric(
        values.astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False),
        errors="coerce",
    )


def _nasdaq_cache_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "cache" / "nasdaq"


def _price_columns_from_multiindex(columns: pd.MultiIndex) -> pd.Index:
    required = set(_REQUIRED_COLUMNS)
    for level in range(columns.nlevels):
        flattened = pd.Index(columns.get_level_values(level))
        titled = flattened.map(lambda column: str(column).strip().title())
        if required.issubset(set(titled)):
            return titled
    raise ValueError("daily bars multi-index is missing a price-column level")


def _bars_in_requested_interval(bars: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    start_timestamp = pd.Timestamp(start)
    end_timestamp = pd.Timestamp(end)
    return bars.loc[(bars.index >= start_timestamp) & (bars.index < end_timestamp)].copy()
