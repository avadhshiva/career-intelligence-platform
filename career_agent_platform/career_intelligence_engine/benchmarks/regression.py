"""Regression snapshot persistence and comparison."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from career_intelligence_engine.intelligence.role_family_scoring import SCORER_PATH
from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.scoring.career_distance import CareerDistanceScorer

_SNAPSHOTS_DIR = Path(__file__).resolve().parent / "snapshots"
_CONTAMINATION_INCREASE_THRESHOLD = 0.15
_CONFIDENCE_COLLAPSE_THRESHOLD = 0.25


@dataclass
class RegressionSnapshot:
    fixture_id: str
    primary: str
    top_rankings: list[dict[str, Any]]
    exclusions: list[str]
    confidence: dict[str, Any]
    contamination_signals: list[dict[str, Any]]
    dominant_dimensions: list[str]
    scorer_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "fixture_id": self.fixture_id,
            "primary": self.primary,
            "top_rankings": self.top_rankings,
            "exclusions": self.exclusions,
            "confidence": self.confidence,
            "contamination_signals": self.contamination_signals,
            "dominant_dimensions": self.dominant_dimensions,
            "scorer_path": self.scorer_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegressionSnapshot:
        return cls(
            fixture_id=str(data["fixture_id"]),
            primary=str(data["primary"]),
            top_rankings=list(data.get("top_rankings") or []),
            exclusions=list(data.get("exclusions") or []),
            confidence=dict(data.get("confidence") or {}),
            contamination_signals=list(data.get("contamination_signals") or []),
            dominant_dimensions=list(data.get("dominant_dimensions") or []),
            scorer_path=str(data.get("scorer_path", SCORER_PATH)),
        )


@dataclass
class RegressionComparison:
    fixture_id: str
    passed: bool
    failures: list[str] = field(default_factory=list)


def snapshots_directory() -> Path:
    _SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    return _SNAPSHOTS_DIR


def snapshot_path(fixture_id: str, directory: Path | None = None) -> Path:
    root = directory or snapshots_directory()
    return root / f"{fixture_id}.json"


def build_snapshot(
    fixture_id: str,
    profile: CandidateProfile,
) -> RegressionSnapshot:
    scorer = CareerDistanceScorer()
    ranked = scorer.rank_role_families(profile)
    trace = profile.explanations.get("score_trace") or []
    primary_row = next((r for r in trace if r.get("is_primary")), {})
    dominant = list(primary_row.get("dominant_dimensions") or [])[:5]

    top_rankings = [
        {
            "family": fid.value,
            "score": round(result.proximity, 4),
            "rank": i + 1,
        }
        for i, (fid, result) in enumerate(ranked[:8])
    ]
    exclusions = list(profile.explanations.get("excluded_from_ranking") or [])
    confidence = dict(profile.explanations.get("confidence") or {})
    if profile.confidence_result:
        confidence = profile.confidence_result.to_dict()

    contamination = list(profile.explanations.get("contamination_signals") or [])

    return RegressionSnapshot(
        fixture_id=fixture_id,
        primary=profile.primary_career_track.value,
        top_rankings=top_rankings,
        exclusions=exclusions,
        confidence=confidence,
        contamination_signals=contamination,
        dominant_dimensions=dominant,
        scorer_path=profile.explanations.get("scorer_path", SCORER_PATH),
    )


def save_snapshot(snapshot: RegressionSnapshot, directory: Path | None = None) -> Path:
    path = snapshot_path(snapshot.fixture_id, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(snapshot.to_dict(), f, indent=2, sort_keys=True)
    return path


def load_snapshot(
    fixture_id: str,
    directory: Path | None = None,
) -> RegressionSnapshot | None:
    path = snapshot_path(fixture_id, directory)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return RegressionSnapshot.from_dict(json.load(f))


def compare_snapshots(
    baseline: RegressionSnapshot,
    current: RegressionSnapshot,
) -> RegressionComparison:
    failures: list[str] = []

    if baseline.primary != current.primary:
        failures.append(
            f"primary changed: {baseline.primary} -> {current.primary}"
        )

    baseline_excluded = set(baseline.exclusions)
    current_eligible = {
        r["family"]
        for r in current.top_rankings
        if r.get("score", 0) > 0
    }
    for fam in baseline_excluded:
        if fam in current_eligible:
            failures.append(f"excluded family {fam} became eligible")

    base_contam = {
        s.get("family"): float(s.get("contamination_score", 0))
        for s in baseline.contamination_signals
    }
    cur_contam = {
        s.get("family"): float(s.get("contamination_score", 0))
        for s in current.contamination_signals
    }
    for fam, cur_score in cur_contam.items():
        base_score = base_contam.get(fam, 0.0)
        if cur_score - base_score > _CONTAMINATION_INCREASE_THRESHOLD:
            failures.append(
                f"contamination increased for {fam}: "
                f"{base_score:.3f} -> {cur_score:.3f}"
            )

    base_conf = float(baseline.confidence.get("confidence_score", 0))
    cur_conf = float(current.confidence.get("confidence_score", 0))
    if base_conf - cur_conf > _CONFIDENCE_COLLAPSE_THRESHOLD:
        failures.append(
            f"confidence collapsed: {base_conf:.3f} -> {cur_conf:.3f}"
        )

    return RegressionComparison(
        fixture_id=baseline.fixture_id,
        passed=len(failures) == 0,
        failures=failures,
    )


def compare_against_baseline(
    fixture_id: str,
    profile: CandidateProfile,
    directory: Path | None = None,
) -> RegressionComparison | None:
    baseline = load_snapshot(fixture_id, directory)
    if baseline is None:
        return None
    current = build_snapshot(fixture_id, profile)
    return compare_snapshots(baseline, current)
