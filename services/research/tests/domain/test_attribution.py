from app.domain.attribution import score_attributions
from app.domain.events import EventEvidence, valid_evidence


def test_attribution_normalizes_supported_events_and_keeps_unexplained_remainder() -> None:
    events = [
        EventEvidence(
            kind="earnings",
            occurred_on="2024-05-22",
            title="Earnings release",
            url="https://example.com/e",
            proximity=1.0,
            repeatability=0.8,
            peer_confirmation=0.2,
        ),
        EventEvidence(
            kind="sector",
            occurred_on="2024-05-22",
            title="Semiconductor ETF move",
            url="https://example.com/s",
            proximity=1.0,
            repeatability=0.5,
            peer_confirmation=0.9,
        ),
    ]

    results = score_attributions(events)

    assert round(sum(item.weight for item in results), 6) == 100.0
    assert results[-1].kind == "unexplained"
    assert results[-1].weight > 0
    assert results[1].weight > results[0].weight


def test_attribution_with_no_valid_evidence_is_fully_unexplained() -> None:
    results = score_attributions([])

    assert [(item.kind, item.weight, item.evidence) for item in results] == [
        ("unexplained", 100.0, None)
    ]


def test_news_without_timestamp_and_url_is_not_used_as_evidence() -> None:
    rumor = EventEvidence(
        kind="news",
        occurred_on="",
        title="rumor",
        url="",
        proximity=1,
        repeatability=1,
        peer_confirmation=1,
    )

    assert valid_evidence(rumor) is False
    assert score_attributions([rumor])[0].kind == "unexplained"
