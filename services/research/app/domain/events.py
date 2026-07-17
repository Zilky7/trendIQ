"""Timestamped event evidence and provider-coverage contracts."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Protocol
from urllib.parse import urlparse


@dataclass(frozen=True)
class EventEvidence:
    """A candidate explanation that can be traced back to its source."""

    kind: str
    occurred_on: str
    title: str
    url: str
    proximity: float
    repeatability: float
    peer_confirmation: float


class CoverageState(StrEnum):
    """Whether a provider can substantiate a requested event dimension."""

    AVAILABLE = "available"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class EventCoverage:
    """Provider result that never substitutes an unavailable source with events."""

    provider: str
    state: CoverageState
    events: tuple[EventEvidence, ...]
    detail: str


class EventProvider(Protocol):
    """Interface implemented by structured and future historical-news providers."""

    def events_between(self, start: str, end: str) -> EventCoverage: ...


def valid_evidence(event: EventEvidence) -> bool:
    """Return true only for evidence with a valid date, title, and HTTP(S) source."""
    try:
        date.fromisoformat(event.occurred_on)
    except ValueError:
        return False

    parsed_url = urlparse(event.url)
    return bool(
        event.title.strip()
        and parsed_url.scheme in {"http", "https"}
        and parsed_url.netloc
    )
