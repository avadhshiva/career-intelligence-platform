"""Load real-world benchmark fixtures from fixtures directory."""

from __future__ import annotations

from pathlib import Path

from career_intelligence_engine.benchmarks.real_world.schema import (
    BenchmarkFixture,
    load_fixture_from_json,
)

_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def fixtures_directory() -> Path:
    return _FIXTURES_DIR


def load_all_fixtures(directory: Path | None = None) -> tuple[BenchmarkFixture, ...]:
    """Load all JSON fixtures sorted by fixture_id (deterministic order)."""
    root = directory or _FIXTURES_DIR
    if not root.exists():
        return ()
    paths = sorted(root.glob("*.json"), key=lambda p: p.name)
    return tuple(load_fixture_from_json(p) for p in paths)


def load_fixture_by_id(
    fixture_id: str,
    directory: Path | None = None,
) -> BenchmarkFixture | None:
    for fixture in load_all_fixtures(directory):
        if fixture.fixture_id == fixture_id:
            return fixture
    return None
