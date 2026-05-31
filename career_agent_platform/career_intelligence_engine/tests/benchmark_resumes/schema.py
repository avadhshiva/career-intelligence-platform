"""Schema for deterministic benchmark resume fixtures."""

from __future__ import annotations

from dataclasses import dataclass, field

from career_intelligence_engine.models.ontology import RoleFamilyId


@dataclass(frozen=True)
class CapabilityTraitRange:
    """Expected normalized capability vector dimension bounds."""

    dimension: str
    min_value: float
    max_value: float


@dataclass(frozen=True)
class BenchmarkResumeFixture:
    """
    Synthetic benchmark fixture: resume text encodes parsed signals;
    expectations encode ontology calibration targets.
    """

    fixture_id: str
    resume_text: str
    expected_primary: RoleFamilyId
    acceptable_primaries: tuple[RoleFamilyId, ...] = ()
    expected_adjacent: tuple[RoleFamilyId, ...] = ()
    forbidden_families: tuple[RoleFamilyId, ...] = ()
    excluded_families: tuple[RoleFamilyId, ...] = ()
    capability_traits: tuple[CapabilityTraitRange, ...] = ()
    must_rank_in_top: tuple[tuple[RoleFamilyId, int], ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        if not self.fixture_id.strip():
            raise ValueError("fixture_id is required")
        if not self.resume_text.strip():
            raise ValueError("resume_text is required")
