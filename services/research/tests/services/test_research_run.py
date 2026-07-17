import json

import pytest

from app.domain.strategy import ResearchWindow
from app.services.research_run import ResearchRun, ResearchRunStore


def test_store_writes_a_serializable_frozen_research_version(tmp_path) -> None:
    store = ResearchRunStore(tmp_path)
    run = ResearchRun(
        version="v1",
        universe=("MU", "MRVL", "SPY"),
        window=ResearchWindow(),
        parameters={"rsi_min": 50},
        development_metrics={"win_rate": 0.55},
        validation_metrics={"win_rate": 0.51},
    )

    path = store.save(run)

    assert json.loads(path.read_text()) == {
        "development_metrics": {"win_rate": 0.55},
        "parameters": {"rsi_min": 50},
        "universe": ["MU", "MRVL", "SPY"],
        "validation_metrics": {"win_rate": 0.51},
        "version": "v1",
        "window": {
            "development_end": "2024-12-31",
            "development_start": "2020-01-01",
            "validation_end": "2025-12-31",
            "validation_start": "2025-01-01",
        },
    }
    assert path.stat().st_mode & 0o222 == 0


def test_store_refuses_to_overwrite_an_existing_research_version(tmp_path) -> None:
    store = ResearchRunStore(tmp_path)
    original = ResearchRun(
        version="v1",
        universe=("MU",),
        window=ResearchWindow(),
        parameters={"rsi_min": 50},
        development_metrics={},
        validation_metrics={},
    )
    replacement = ResearchRun(
        version="v1",
        universe=("NOK",),
        window=ResearchWindow(),
        parameters={"rsi_min": 60},
        development_metrics={},
        validation_metrics={},
    )
    store.save(original)

    with pytest.raises(ValueError, match="research version already exists: v1"):
        store.save(replacement)


def test_store_rejects_nonserializable_content_without_creating_a_version_file(tmp_path) -> None:
    store = ResearchRunStore(tmp_path)
    run = ResearchRun(
        version="invalid",
        universe=("MU",),
        window=ResearchWindow(),
        parameters={"unsupported": {"set values are not JSON"}},
        development_metrics={},
        validation_metrics={},
    )

    with pytest.raises(TypeError):
        store.save(run)

    assert not (tmp_path / "invalid.json").exists()
