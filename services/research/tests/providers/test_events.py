from app.providers.events import MacroEventProvider, UnavailableEventProvider
from app.domain.events import CoverageState


def test_macro_provider_returns_timestamped_official_fomc_cpi_and_nfp_events() -> None:
    coverage = MacroEventProvider().events_between("2024-01-01", "2024-02-13")

    assert coverage.state is CoverageState.PARTIAL
    assert {event.kind for event in coverage.events} == {"fomc", "cpi", "nfp"}
    assert all(event.occurred_on and event.url.startswith("https://") for event in coverage.events)
    fomc_event = next(event for event in coverage.events if event.kind == "fomc")
    assert fomc_event.url == (
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240131a.htm"
    )


def test_macro_provider_marks_dates_outside_its_static_catalog_as_unavailable() -> None:
    coverage = MacroEventProvider().events_between("2020-01-01", "2020-12-31")

    assert coverage.state is CoverageState.UNAVAILABLE
    assert coverage.events == ()


def test_unavailable_provider_returns_typed_uncovered_state_without_events() -> None:
    coverage = UnavailableEventProvider("historical_news").events_between(
        "2024-01-01", "2024-01-31"
    )

    assert coverage.provider == "historical_news"
    assert coverage.state is CoverageState.UNAVAILABLE
    assert coverage.events == ()
