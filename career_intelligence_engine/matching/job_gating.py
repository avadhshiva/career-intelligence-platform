"""Hard gating for candidate ↔ job match — reuses calibration gate thresholds."""

from __future__ import annotations

from dataclasses import dataclass

from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.job_profile import JobProfile
from career_intelligence_engine.ontology.role_family_calibration import (
    ARCH_GATE,
    DIMENSION_GATES,
    OPS_GATE,
    PRODUCT_GATE,
)

_PRODUCT_GATE = PRODUCT_GATE
_OPS_GATE = OPS_GATE
_ARCH_GATE = ARCH_GATE


@dataclass
class JobGateResult:
    passed: bool
    capped_score: float | None
    reasons: list[str]
    eligibility_fit: float


def _candidate_product_depth(profile: CandidateProfile) -> float:
    raw = profile.capability_raw_scores or {}
    return max(
        raw.get("product_ownership_depth", 0.0),
        raw.get("product_thinking", 0.0),
    )


def _candidate_ops_depth(profile: CandidateProfile) -> float:
    raw = profile.capability_raw_scores or {}
    ops_dim = raw.get("operational_management", 0.0)
    if ops_dim <= 0.0:
        return 0.0
    return max(raw.get("operational_run_depth", 0.0), ops_dim)


def _candidate_arch_depth(profile: CandidateProfile) -> float:
    raw = profile.capability_raw_scores or {}
    return raw.get("architecture_coordination", 0.0)


def evaluate_job_gates(
    profile: CandidateProfile,
    job: JobProfile,
) -> JobGateResult:
    """
    Apply deterministic hard gates when the JD requires product, ops, or architecture depth.
    Mirrors role_family_calibration exclusion logic for candidate evidence.
    """
    reasons: list[str] = []
    passed = True
    capped: float | None = None
    eligibility = 1.0

    product_depth = _candidate_product_depth(profile)
    ops_depth = _candidate_ops_depth(profile)
    arch_depth = _candidate_arch_depth(profile)

    if job.is_product_heavy or job.product_ownership_required >= PRODUCT_GATE:
        if product_depth < PRODUCT_GATE:
            passed = False
            capped = 0.32
            eligibility = min(eligibility, 0.25)
            reasons.append(
                f"Product gate failed: candidate product depth {product_depth:.3f} "
                f"< required {PRODUCT_GATE} (roadmap/customer ownership evidence missing)"
            )

    if job.is_operations_heavy or job.operational_ownership_required >= OPS_GATE:
        if ops_depth < OPS_GATE:
            passed = False
            capped = min(capped or 0.30, 0.30)
            eligibility = min(eligibility, 0.20)
            reasons.append(
                f"Operations gate failed: candidate ops depth {ops_depth:.3f} "
                f"< required {OPS_GATE} (run-state operational evidence missing)"
            )

    if job.is_architecture_heavy or job.architecture_depth >= ARCH_GATE:
        if arch_depth <= 0.0:
            passed = False
            capped = min(capped or 0.35, 0.35)
            eligibility = min(eligibility, 0.30)
            reasons.append(
                f"Architecture gate failed: candidate architecture_coordination "
                f"{arch_depth:.3f} — architecture-heavy role requires architecture evidence"
            )

    if job.is_release_governance_heavy:
        release_raw = (profile.capability_raw_scores or {}).get("release_governance", 0.0)
        tech_raw = (profile.capability_raw_scores or {}).get("technical_execution", 0.0)
        if release_raw < 0.15 and tech_raw < 0.15:
            eligibility = min(eligibility, 0.45)
            reasons.append(
                "Release governance role: limited release train / SDLC governance evidence"
            )

    if job.is_ai_transformation:
        ai_raw = (profile.capability_raw_scores or {}).get("ai_strategy", 0.0)
        trans_raw = (profile.capability_raw_scores or {}).get("transformation_strategy", 0.0)
        if ai_raw < 0.20 and trans_raw < 0.20:
            eligibility = min(eligibility, 0.40)
            reasons.append(
                "AI transformation role: limited AI strategy and transformation ownership evidence"
            )

    if not passed and capped is None:
        capped = 0.35

    return JobGateResult(
        passed=passed,
        capped_score=capped,
        reasons=reasons,
        eligibility_fit=round(eligibility, 4),
    )
