from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


FrameReader = Callable[[Path], pd.DataFrame]
FrameWriter = Callable[[pd.DataFrame, Path], None]


@dataclass(frozen=True)
class _CacheInterval:
    path: Path
    start: str
    end: str

    def fully_covers(self, start: str, end: str) -> bool:
        return self.start <= start and self.end >= end


class BarCache:
    def __init__(
        self,
        cache_dir: Path | None = None,
        read_frame: FrameReader = pd.read_parquet,
        write_frame: FrameWriter = lambda frame, path: frame.to_parquet(path),
    ) -> None:
        self.cache_dir = cache_dir or _default_cache_dir()
        self.read_frame = read_frame
        self.write_frame = write_frame

    def get(self, symbol: str, start: str, end: str) -> pd.DataFrame | None:
        request_start = _date_key(start)
        request_end = _date_key(end)
        candidates = [
            interval
            for interval in self._intervals_for(symbol)
            if interval.fully_covers(request_start, request_end)
        ]
        if not candidates:
            return None

        smallest_covering_interval = min(
            candidates,
            key=lambda interval: (interval.end, interval.start),
        )
        try:
            return self.read_frame(smallest_covering_interval.path)
        except (OSError, ValueError, ImportError):
            return None

    def put(self, symbol: str, start: str, end: str, bars: pd.DataFrame) -> Path:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self.cache_dir / _cache_filename(symbol, start, end)
        temporary_path = path.with_suffix(".tmp")
        try:
            self.write_frame(bars, temporary_path)
            temporary_path.replace(path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
        return path

    def _intervals_for(self, symbol: str) -> list[_CacheInterval]:
        normalized_symbol = symbol.upper()
        prefix = f"{normalized_symbol}__"
        intervals = []
        for path in self.cache_dir.glob(f"{prefix}*.parquet"):
            parts = path.stem.split("__")
            if len(parts) != 3:
                continue
            _, start, end = parts
            try:
                intervals.append(_CacheInterval(path, _date_key(start), _date_key(end)))
            except ValueError:
                continue
        return intervals


def _default_cache_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "cache"


def _cache_filename(symbol: str, start: str, end: str) -> str:
    return f"{symbol.upper()}__{_date_key(start)}__{_date_key(end)}.parquet"


def _date_key(value: str) -> str:
    return pd.Timestamp(value).date().isoformat()
