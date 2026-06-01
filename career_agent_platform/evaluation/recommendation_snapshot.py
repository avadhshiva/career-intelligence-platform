"""Serialize recommendation runs for deterministic comparison over time."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from recommendation_engine import RecommendationResult


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


@dataclass
class RecommendationSnapshot:
    """Normalized view of a recommendation run for diffing."""

    snapshot_id: str
    created_at: str
    resume_fingerprint: str
    profile_primary_track: str
    ontology_version: str
    recommendation_hash: str
    items: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecommendationSnapshot:
        return cls(
            snapshot_id=str(data["snapshot_id"]),
            created_at=str(data.get("created_at", "")),
            resume_fingerprint=str(data.get("resume_fingerprint", "")),
            profile_primary_track=str(data.get("profile_primary_track", "")),
            ontology_version=str(data.get("ontology_version", "")),
            recommendation_hash=str(data.get("recommendation_hash", "")),
            items=list(data.get("items") or []),
            metadata=dict(data.get("metadata") or {}),
        )


def resume_fingerprint(resume_text: str) -> str:
    normalized = " ".join(resume_text.split()).strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _normalize_item(rec: "RecommendationResult | dict[str, Any]") -> dict[str, Any]:
    from recommendation_engine import RecommendationResult

    if isinstance(rec, RecommendationResult):
        data = rec.to_dict()
    else:
        data = dict(rec)
    detail = dict(data.get("match_detail") or {})
    diagnostics = dict(detail.get("diagnostics") or {})
    return {
        "job_id": str(data.get("job_id", "")),
        "job_title": str(data.get("job_title", "")),
        "company": str(data.get("company", "")),
        "overall_match": round(float(data.get("overall_match", 0.0)), 6),
        "confidence": round(float(data.get("confidence", 0.0)), 6),
        "recommendation_priority": str(data.get("recommendation_priority", "")),
        "eligibility_passed": bool(data.get("eligibility_passed", False)),
        "primary_role_family": str(detail.get("primary_role_family", "")),
        "dominant_dimensions": list(data.get("dominant_dimensions") or [])[:8],
        "missing_dimensions": list(data.get("missing_dimensions") or [])[:8],
        "role_cluster": diagnostics.get("role_cluster") or detail.get("primary_role_family", ""),
    }


def recommendation_hash(items: list[dict[str, Any]]) -> str:
    payload = [
        {
            "job_id": i["job_id"],
            "overall_match": i["overall_match"],
            "recommendation_priority": i["recommendation_priority"],
            "primary_role_family": i.get("primary_role_family", ""),
        }
        for i in items
    ]
    return _stable_hash({"ordering": payload})


def capture_snapshot(
    recommendations: "list[RecommendationResult]",
    *,
    resume_text: str = "",
    profile_primary_track: str = "",
    ontology_version: str = "",
    label: str = "",
    created_at: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> RecommendationSnapshot:
    """Build an in-memory snapshot from a recommendation run."""
    from career_intelligence_engine.ontology.version import get_ontology_version

    items = [_normalize_item(r) for r in recommendations]
    rec_hash = recommendation_hash(items)
    created = created_at if created_at is not None else _utc_now_iso()
    snap_id = _stable_hash(
        {
            "resume": resume_fingerprint(resume_text) if resume_text else "",
            "rec_hash": rec_hash,
            "label": label,
        },
    )
    return RecommendationSnapshot(
        snapshot_id=snap_id,
        created_at=created,
        resume_fingerprint=resume_fingerprint(resume_text) if resume_text else "",
        profile_primary_track=profile_primary_track,
        ontology_version=ontology_version or get_ontology_version(),
        recommendation_hash=rec_hash,
        items=items,
        metadata={"label": label, **(metadata or {})},
    )


def write_snapshot(path: str | Path, snapshot: RecommendationSnapshot) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")
    return out


def load_snapshot(path: str | Path) -> RecommendationSnapshot:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return RecommendationSnapshot.from_dict(data)
