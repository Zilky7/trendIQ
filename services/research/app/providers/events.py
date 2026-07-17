"""Structured event sources; unavailable coverage is never fabricated."""

from app.domain.events import CoverageState, EventCoverage, EventEvidence


class UnavailableEventProvider:
    """A typed placeholder for a provider that has not been configured yet."""

    def __init__(self, provider_name: str, detail: str = "provider is not configured") -> None:
        self._provider_name = provider_name
        self._detail = detail

    def events_between(self, start: str, end: str) -> EventCoverage:
        return EventCoverage(
            provider=self._provider_name,
            state=CoverageState.UNAVAILABLE,
            events=(),
            detail=self._detail,
        )


class EarningsSecEventProvider(UnavailableEventProvider):
    """Coverage contract for a future earnings-calendar and SEC metadata source."""

    def __init__(self) -> None:
        super().__init__("earnings_sec", "earnings and SEC provider is not configured")


class MacroEventProvider:
    """Small, static catalog of official macro release records used in development.

    These are historical calendar facts, not a live-event feed.  More dates can
    be added only with their official publication URLs.
    """

    _EVENTS = (
        EventEvidence(
            kind="fomc",
            occurred_on="2024-01-31",
            title="FOMC statement",
            url="https://www.federalreserve.gov/newsevents/pressreleases/monetary20240131a.htm",
            proximity=1.0,
            repeatability=1.0,
            peer_confirmation=0.5,
        ),
        EventEvidence(
            kind="nfp",
            occurred_on="2024-02-02",
            title="Employment Situation, January 2024",
            url="https://www.bls.gov/news.release/archives/empsit_02022024.htm",
            proximity=1.0,
            repeatability=1.0,
            peer_confirmation=0.5,
        ),
        EventEvidence(
            kind="cpi",
            occurred_on="2024-02-13",
            title="Consumer Price Index, January 2024",
            url="https://www.bls.gov/news.release/archives/cpi_02132024.htm",
            proximity=1.0,
            repeatability=1.0,
            peer_confirmation=0.5,
        ),
    )
    _CATALOG_START = "2024-01-01"
    _CATALOG_END = "2024-12-31"

    def events_between(self, start: str, end: str) -> EventCoverage:
        if end < self._CATALOG_START or start > self._CATALOG_END:
            return EventCoverage(
                provider="official_macro_calendar",
                state=CoverageState.UNAVAILABLE,
                events=(),
                detail="static macro catalog only covers selected 2024 release records",
            )

        events = tuple(event for event in self._EVENTS if start <= event.occurred_on <= end)
        return EventCoverage(
            provider="official_macro_calendar",
            state=CoverageState.PARTIAL,
            events=events,
            detail="partial static catalog of official 2024 FOMC, CPI, and NFP records",
        )
