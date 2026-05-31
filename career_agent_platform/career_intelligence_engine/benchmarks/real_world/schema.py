"""Schema for real-world anonymized resume benchmark fixtures."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class BenchmarkFixture:
    fixture_id: str
    resume_text: str
    expected_primary: str
    acceptable_primaries: list[str] = field(default_factory=list)
    allowed_adjacent: list[str] = field(default_factory=list)
    forbidden_families: list[str] = field(default_factory=list)
    expected_exclusions: list[str] = field(default_factory=list)
    minimum_confidence: float = 0.0

    def __post_init__(self) -> None:
        if not self.fixture_id.strip():
            raise ValueError("fixture_id is required")
        if not self.resume_text.strip():
            raise ValueError("resume_text is required")
        if not self.expected_primary.strip():
            raise ValueError("expected_primary is required")

    @classmethod
    def from_dict(cls, data: dict) -> BenchmarkFixture:
        return cls(
            fixture_id=str(data["fixture_id"]),
            resume_text=str(data.get("resume_text", "")),
            expected_primary=str(data["expected_primary"]),
            acceptable_primaries=list(data.get("acceptable_primaries") or []),
            allowed_adjacent=list(data.get("allowed_adjacent") or []),
            forbidden_families=list(data.get("forbidden_families") or []),
            expected_exclusions=list(data.get("expected_exclusions") or []),
            minimum_confidence=float(data.get("minimum_confidence", 0.0)),
        )

    def to_dict(self) -> dict:
        return {
            "fixture_id": self.fixture_id,
            "resume_text": self.resume_text,
            "expected_primary": self.expected_primary,
            "acceptable_primaries": list(self.acceptable_primaries),
            "allowed_adjacent": list(self.allowed_adjacent),
            "forbidden_families": list(self.forbidden_families),
            "expected_exclusions": list(self.expected_exclusions),
            "minimum_confidence": self.minimum_confidence,
        }


def load_fixture_from_json(path: Path) -> BenchmarkFixture:
    with path.open(encoding="utf-8") as f:
        return BenchmarkFixture.from_dict(json.load(f))


def load_fixture_from_txt(path: Path, meta_path: Path | None = None) -> BenchmarkFixture:
    """Load resume text from .txt and metadata from companion .json if present."""
    resume_text = path.read_text(encoding="utf-8")
    meta_file = meta_path or path.with_suffix(".json")
    if meta_file.exists():
        return load_fixture_from_json(meta_file)
    raise ValueError(f"Metadata JSON required for txt fixture: {meta_file}")
