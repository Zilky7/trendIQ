"""Deterministic, evidence-only explanation weights for price moves."""

from dataclasses import dataclass

from .events import EventEvidence, valid_evidence


# The research specification maps one unit of independently corroborated
# support to 50 explanatory percentage points.  The calibration caps all
# evidence at 85%, retaining at least 15% for causes not represented in data.
EXPLAINED_PERCENT_PER_SUPPORT_POINT = 50.0
MAX_EXPLAINED_PERCENT = 85.0
PERCENT = 100.0


@dataclass(frozen=True)
class Attribution:
    kind: str
    weight: float
    confidence: str
    evidence: EventEvidence | None


def score_attributions(events: list[EventEvidence]) -> list[Attribution]:
    """Allocate a bounded evidence share and retain the unexplained balance.

    Each input factor is constrained to its evidence scale of zero through one.
    Their product is the event's deterministic support score.  The aggregate
    support is converted to explained coverage using the frozen research
    calibration, while each event receives its proportional portion.
    """
    supported = [event for event in events if valid_evidence(event)]
    raw_scores = [_support_score(event) for event in supported]
    total_support = sum(raw_scores)
    explained_percent = min(
        MAX_EXPLAINED_PERCENT,
        total_support * EXPLAINED_PERCENT_PER_SUPPORT_POINT,
    )

    if total_support == 0:
        return [_unexplained(PERCENT)]

    weights = [explained_percent * score / total_support for score in raw_scores]
    attributions = [
        Attribution(
            kind=event.kind,
            weight=weight,
            confidence=_confidence(weight),
            evidence=event,
        )
        for event, weight in zip(supported, weights, strict=True)
    ]
    unexplained_weight = PERCENT - sum(weights)
    return attributions + [_unexplained(unexplained_weight)]


def _support_score(event: EventEvidence) -> float:
    return (
        _unit_interval(event.proximity)
        * _unit_interval(event.repeatability)
        * _unit_interval(event.peer_confirmation)
    )


def _unit_interval(value: float) -> float:
    return min(1.0, max(0.0, value))


def _confidence(weight: float) -> str:
    if weight >= 25.0:
        return "high"
    if weight >= 10.0:
        return "medium"
    return "low"


def _unexplained(weight: float) -> Attribution:
    return Attribution("unexplained", weight, "low", None)
