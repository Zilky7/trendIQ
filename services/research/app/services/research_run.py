"""Persistence for frozen, reproducible strategy research versions."""

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Mapping

from app.domain.strategy import ResearchWindow


_VERSION_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class ResearchRun:
    version: str
    universe: tuple[str, ...]
    window: ResearchWindow
    parameters: Mapping[str, object]
    development_metrics: Mapping[str, object]
    validation_metrics: Mapping[str, object]

    def to_record(self) -> dict[str, object]:
        """Return a JSON-serializable record with a stable field contract."""
        return {
            "version": self.version,
            "universe": list(self.universe),
            "window": asdict(self.window),
            "parameters": dict(self.parameters),
            "development_metrics": dict(self.development_metrics),
            "validation_metrics": dict(self.validation_metrics),
        }


class ResearchRunStore:
    """Append-only JSON storage; a strategy version cannot be replaced."""

    def __init__(self, runs_directory: Path) -> None:
        self._runs_directory = runs_directory

    def save(self, run: ResearchRun) -> Path:
        if not _VERSION_NAME.fullmatch(run.version):
            raise ValueError("research version must be a simple file name")

        serialized_record = json.dumps(run.to_record(), indent=2, sort_keys=True) + "\n"
        self._runs_directory.mkdir(parents=True, exist_ok=True)
        path = self._runs_directory / f"{run.version}.json"

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self._runs_directory,
                prefix=f".{run.version}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(serialized_record)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            temporary_path.chmod(0o444)
            try:
                os.link(temporary_path, path)
            except FileExistsError as error:
                raise ValueError(f"research version already exists: {run.version}") from error
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

        return path
