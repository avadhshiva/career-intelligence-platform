"""Role Family Separation Calibration V2 — gates, contamination suppression, cluster separation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from career_intelligence_engine.models.ontology import RoleFamilyId

# ---------------------------------------------------------------------------
# Part 1 — Strong positive gates (family-specific evidence)
# ---------------------------------------------------------------------------

_FAMILY_GATE_PATTERNS: dict[RoleFamilyId, list[re.Pattern[str]]] = {
    RoleFamilyId.AI_TRANSFORMATION: [
        re.compile(p, re.I)
        for p in (
            r"\bai strategy\b",
            r"\bai transformation\b",
            r"\benterprise ai\b",
            r"\bgenai\b",
            r"\bresponsible ai\b",
            r"\bai operating model\b",
        )
    ],
    RoleFamilyId.RELEASE_GOVERNANCE: [
        re.compile(p, re.I)
        for p in (
            r"\brelease train\b",
            r"\bcab\b|\bchange advisory\b",
            r"\bdeployment governance\b",
            r"\bsdlc governance\b",
            r"\bcutover\b",
            r"\bproduction release\b",
            r"\brelease cadence\b",
            r"\brelease governance\b",
            r"\bquality gate\b",
        )
    ],
    RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT: [
        re.compile(p, re.I)
        for p in (
            r"\barchitecture coordination\b|\barchitecture alignment\b",
            r"\btechnical dependency management\b|\bdependency management\b",
            r"\bengineering coordination\b",
            r"\bintegration delivery\b|\bsystem integration\b",
            r"\bplatform\b.{0,30}\btechnical\b|\btechnical program\b",
            r"\bengineering roadmap\b",
        )
    ],
    RoleFamilyId.PROGRAM_LEADERSHIP: [
        re.compile(p, re.I)
        for p in (
            r"\bpmo\b|\bprogram management office\b",
            r"\bportfolio governance\b",
            r"\bsteering committee\b",
            r"\bbudget(?:ing)?\b",
            r"\bexecutive program review\b",
            r"\bmulti-?program orchestration\b|\binitiative portfolio\b",
            r"\bbenefits realization\b",
        )
    ],
    RoleFamilyId.ENTERPRISE_DELIVERY: [
        re.compile(p, re.I)
        for p in (
            r"\benterprise rollout\b|\bglobal rollout\b",
            r"\bdelivery governance\b",
            r"\boperational execution\b",
            r"\bdelivery assurance\b",
            r"\benterprise-?scale implementation\b",
            r"\bclient delivery lead\b|\bimplementation lead\b",
            r"\berp implementation\b|\bcrm implementation\b",
        )
    ],
    RoleFamilyId.AI_GOVERNANCE: [
        re.compile(p, re.I)
        for p in (
            r"\bai governance\b",
            r"\bresponsible ai\b",
            r"\bmodel governance\b",
            r"\bai ethics\b",
            r"\bmodel risk\b",
            r"\bai policy\b",
        )
    ],
    RoleFamilyId.CLOUD_TRANSFORMATION: [
        re.compile(p, re.I)
        for p in (
            r"\bcloud transformation\b",
            r"\bcloud migration\b",
            r"\baws migration\b|\bazure migration\b",
            r"\bmulti-?cloud\b",
            r"\bcloud operating model\b",
            r"\blanding zone\b",
        )
    ],
}

_GATE_MIN_HITS = 2
_GATE_STRONG_HITS = 4

# ---------------------------------------------------------------------------
# Part 2 — Explicit domain evidence (contamination suppression bypass)
# ---------------------------------------------------------------------------

_EXPLICIT_SALES_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\bquota\b",
        r"\bpipeline ownership\b|\bsales pipeline\b",
        r"\brevenue targets?\b",
        r"\baccount expansion\b",
        r"\bgtm ownership\b|\bgo-to-market ownership\b",
        r"\bquota attainment\b",
    )
]

_EXPLICIT_HR_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\btalent acquisition\b",
        r"\bworkforce planning\b",
        r"\bhrbp\b|\bhr business partner\b",
        r"\bcompensation\b",
        r"\bemployee relations\b",
        r"\brecruiting\b",
        r"\bhr director\b|\bhuman resources\b",
    )
]

_EXPLICIT_FINANCE_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\bfp&a\b",
        r"\bcontrollership\b",
        r"\btreasury\b",
        r"\baudit ownership\b",
        r"\bp&l\b|\bprofit and loss\b",
        r"\bfinancial planning\b",
        r"\bfinancial modeling\b",
    )
]

_CONTAMINATION_FAMILIES = (
    RoleFamilyId.HR,
    RoleFamilyId.SALES,
    RoleFamilyId.FINANCE,
)

_SUPPRESSION_CAP = 0.16
_SUPPRESSION_PENALTY = 0.50

_TRANSFORMATION_INFLATION_FAMILIES = frozenset(
    {
        RoleFamilyId.CLOUD_TRANSFORMATION,
        RoleFamilyId.DIGITAL_TRANSFORMATION,
        RoleFamilyId.AI_PROGRAM_MANAGEMENT,
        RoleFamilyId.TRANSFORMATION_OFFICE,
    }
)

# Indirect architecture coordination (Part 3) — corpus-level boost input
_INDIRECT_ARCHITECTURE_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\bintegration\b",
        r"\bplatform migration\b",
        r"\berp implementation\b",
        r"\bazure delivery\b|\bazure migration\b",
        r"\bdevops coordination\b",
        r"\bsystem rollout\b",
        r"\btechnical dependency\b",
    )
]

_ENGINEERING_DEPTH_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\bsoftware engineer\b",
        r"\bcode review\b",
        r"\bunit testing\b",
        r"\bpull request\b",
        r"\bfull stack\b",
    )
]


@dataclass
class SeparationV2Context:
    """Deterministic separation state derived from resume corpus."""

    corpus_lower: str = ""
    family_gate_scores: dict[str, float] = field(default_factory=dict)
    explicit_hr: bool = False
    explicit_sales: bool = False
    explicit_finance: bool = False
    delivery_governance_dominant: bool = False
    indirect_architecture_hits: int = 0
    signals: list[str] = field(default_factory=list)
    contamination_suppressed: list[str] = field(default_factory=list)


def _pattern_hit_count(corpus: str, patterns: list[re.Pattern[str]]) -> int:
    return sum(len(p.findall(corpus)) for p in patterns)


def _gate_score(hits: int) -> float:
    if hits <= 0:
        return 0.0
    if hits >= _GATE_STRONG_HITS:
        return 1.0
    if hits >= _GATE_MIN_HITS:
        return 0.55 + (hits - _GATE_MIN_HITS) * 0.15
    return 0.25 * hits


def build_separation_v2_context(corpus: str, raw_scores: dict[str, float]) -> SeparationV2Context:
    """Analyze corpus and capability raw scores for V2 calibration."""
    lower = corpus.lower()
    ctx = SeparationV2Context(corpus_lower=lower)

    for family_id, patterns in _FAMILY_GATE_PATTERNS.items():
        hits = _pattern_hit_count(lower, patterns)
        ctx.family_gate_scores[family_id.value] = round(_gate_score(hits), 4)

    ctx.explicit_hr = _pattern_hit_count(lower, _EXPLICIT_HR_PATTERNS) >= 1
    ctx.explicit_sales = _pattern_hit_count(lower, _EXPLICIT_SALES_PATTERNS) >= 1
    ctx.explicit_finance = _pattern_hit_count(lower, _EXPLICIT_FINANCE_PATTERNS) >= 1

    ctx.indirect_architecture_hits = _pattern_hit_count(lower, _INDIRECT_ARCHITECTURE_PATTERNS)

    tech = float(raw_scores.get("technical_execution", 0.0))
    rel = float(raw_scores.get("release_governance", 0.0))
    gov = float(raw_scores.get("enterprise_governance", 0.0))
    deliv = float(raw_scores.get("delivery_execution", 0.0))
    arch = float(raw_scores.get("architecture_coordination", 0.0))

    port = float(raw_scores.get("portfolio_management", 0.0))
    cluster_gate = max(
        ctx.family_gate_scores.get(RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT.value, 0.0),
        ctx.family_gate_scores.get(RoleFamilyId.RELEASE_GOVERNANCE.value, 0.0),
        ctx.family_gate_scores.get(RoleFamilyId.PROGRAM_LEADERSHIP.value, 0.0),
        ctx.family_gate_scores.get(RoleFamilyId.ENTERPRISE_DELIVERY.value, 0.0),
    )
    ctx.delivery_governance_dominant = (
        tech >= 0.12
        or rel >= 0.12
        or gov >= 0.15
        or deliv >= 0.18
        or arch >= 0.12
        or port >= 0.18
        or cluster_gate >= 0.55
    )

    if ctx.delivery_governance_dominant and not ctx.explicit_hr:
        ctx.signals.append("delivery_governance_profile")
    if ctx.indirect_architecture_hits >= 2:
        ctx.signals.append("indirect_architecture_evidence")

    return ctx


_DIRECT_ARCHITECTURE_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\barchitecture review\b",
        r"\bsolution architecture\b",
        r"\benterprise architecture\b",
        r"\barchitecture board\b",
        r"\btechnical architecture\b",
        r"\bdesign authority\b",
    )
]


def apply_indirect_architecture_boost(
    raw_scores: dict[str, float],
    corpus: str,
) -> tuple[dict[str, float], list[str]]:
    """
    Boost architecture_coordination from indirect TPM signals.
    Does not inflate engineering_depth without hands-on engineering evidence.
    """
    lower = corpus.lower()
    direct_hits = _pattern_hit_count(lower, _DIRECT_ARCHITECTURE_PATTERNS)
    indirect_hits = _pattern_hit_count(lower, _INDIRECT_ARCHITECTURE_PATTERNS)
    signals: list[str] = []
    if indirect_hits == 0:
        return raw_scores, signals

    eng_hits = _pattern_hit_count(lower, _ENGINEERING_DEPTH_PATTERNS)
    current = float(raw_scores.get("architecture_coordination", 0.0))
    if direct_hits >= 2:
        return raw_scores, signals

    boost = min(0.16, 0.05 * indirect_hits)
    if direct_hits == 1:
        boost = min(boost, 0.10)
    updated = dict(raw_scores)
    updated["architecture_coordination"] = round(
        min(0.48, current + boost), 3
    )
    signals.append(
        f"architecture_coordination +{boost:.2f} from indirect coordination signals "
        f"({indirect_hits} hits)"
    )

    if eng_hits == 0:
        eng = float(updated.get("engineering_depth", 0.0))
        updated["engineering_depth"] = round(min(eng, 0.28), 3)

    return updated, signals


def apply_separation_v2_proximity(
    family_id: RoleFamilyId,
    proximity: float,
    raw_scores: dict[str, float],
    sep: SeparationV2Context,
) -> tuple[float, float, str | None]:
    """
    Apply V2 proximity adjustments. Returns (adjusted_proximity, penalty, explanation).
    """
    penalty = 0.0
    explanations: list[str] = []

    gate = sep.family_gate_scores.get(family_id.value, 0.0)
    tpm_gate = sep.family_gate_scores.get(
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT.value, 0.0
    )
    pl_gate = sep.family_gate_scores.get(RoleFamilyId.PROGRAM_LEADERSHIP.value, 0.0)
    release_gate = sep.family_gate_scores.get(RoleFamilyId.RELEASE_GOVERNANCE.value, 0.0)
    delivery_gate = sep.family_gate_scores.get(RoleFamilyId.ENTERPRISE_DELIVERY.value, 0.0)

    # Part 1 — positive gate penalties for enterprise delivery cluster
    skip_gate_penalty = (
        family_id == RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT and tpm_gate <= 0.0
    )
    if family_id in _FAMILY_GATE_PATTERNS and not skip_gate_penalty:
        if gate < 0.35:
            if gate <= 0.0:
                p = 0.08
            elif gate < 0.2:
                p = 0.14
            else:
                p = 0.10
            penalty += p
            if p >= 0.10:
                explanations.append(
                    _gate_missing_message(family_id, gate)
                )
        elif gate >= 0.55:
            explanations.append(
                f"Strong {ROLE_FAMILY_LABELS.get(family_id, family_id.value)} evidence "
                f"({gate:.0%} gate match)."
            )

    if family_id == RoleFamilyId.ENTERPRISE_DELIVERY and tpm_gate >= 0.55:
        if (
            "technical program manager" in sep.corpus_lower
            or "technical program management" in sep.corpus_lower
        ):
            penalty += 0.16
            explanations.append(
                "Enterprise Delivery proximity reduced — technical program management "
                "gated evidence outweighs generic delivery language."
            )

    # Release vs Enterprise Delivery separation
    if family_id == RoleFamilyId.ENTERPRISE_DELIVERY and release_gate >= 0.55 and delivery_gate < 0.45:
        penalty += 0.18
        explanations.append(
            "Enterprise Delivery proximity reduced because release-governance evidence "
            "is stronger than enterprise implementation language."
        )
    if family_id == RoleFamilyId.PROGRAM_LEADERSHIP and delivery_gate >= 0.55 and gate < 0.45:
        penalty += 0.12
        explanations.append(
            "Program Leadership proximity reduced due to delivery-heavy language without "
            "PMO or portfolio governance evidence."
        )
    if family_id == RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT:
        arch = float(raw_scores.get("architecture_coordination", 0.0))
        if arch < 0.14 and gate < 0.45 and tpm_gate > 0.0:
            penalty += 0.10

    if (
        family_id == RoleFamilyId.PROGRAM_LEADERSHIP
        and tpm_gate >= 0.55
        and tpm_gate > pl_gate + 0.05
    ):
        penalty += 0.22
        explanations.append(
            "Program Leadership proximity reduced — technical program management "
            "gated evidence is stronger for this profile."
        )
    if family_id == RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT and tpm_gate >= 0.55:
        penalty = max(0.0, penalty - 0.12)

    if (
        family_id == RoleFamilyId.RELEASE_GOVERNANCE
        and tpm_gate >= 0.55
        and tpm_gate >= release_gate - 0.05
        and (
            "technical program manager" in sep.corpus_lower
            or "technical program management" in sep.corpus_lower
        )
        and "release governance lead" not in sep.corpus_lower
        and "release manager" not in sep.corpus_lower
    ):
        penalty += 0.22
        explanations.append(
            "Release Governance proximity reduced — technical program management "
            "title and gated evidence dominate over ancillary release-train language."
        )

    if family_id in _TRANSFORMATION_INFLATION_FAMILIES and sep.delivery_governance_dominant:
        if max(tpm_gate, release_gate) >= 0.55:
            to_gate = sep.family_gate_scores.get(
                RoleFamilyId.TRANSFORMATION_OFFICE.value, 0.0
            )
            if family_id == RoleFamilyId.TRANSFORMATION_OFFICE and to_gate >= 0.55:
                pass
            else:
                penalty += 0.34
                explanations.append(
                    f"{ROLE_FAMILY_LABELS.get(family_id, family_id.value)} proximity "
                    "reduced on a delivery-governance profile without matching "
                    "transformation-office evidence."
                )

    if family_id == RoleFamilyId.ENTERPRISE_ARCHITECTURE_DELIVERY:
        direct_arch = _pattern_hit_count(sep.corpus_lower, _DIRECT_ARCHITECTURE_PATTERNS)
        if direct_arch < 1 and delivery_gate >= 0.45 and release_gate < 0.55:
            penalty += 0.20
            explanations.append(
                "Enterprise Architecture proximity reduced — implementation delivery "
                "language without architecture board or design authority evidence."
            )

    ai_gov_gate = sep.family_gate_scores.get(RoleFamilyId.AI_GOVERNANCE.value, 0.0)
    if ai_gov_gate >= 0.55 and family_id == RoleFamilyId.SALES and not sep.explicit_sales:
        penalty += 0.32
        explanations.append(
            "Sales proximity suppressed — AI governance profile without explicit "
            "quota, pipeline, or revenue ownership evidence."
        )

    # Part 2 — contamination suppression
    if family_id in _CONTAMINATION_FAMILIES and sep.delivery_governance_dominant:
        explicit = {
            RoleFamilyId.HR: sep.explicit_hr,
            RoleFamilyId.SALES: sep.explicit_sales,
            RoleFamilyId.FINANCE: sep.explicit_finance,
        }[family_id]
        if not explicit:
            before = proximity - penalty
            capped = min(before, _SUPPRESSION_CAP)
            sup_penalty = max(0.0, before - capped) + _SUPPRESSION_PENALTY
            penalty += sup_penalty
            label = ROLE_FAMILY_LABELS.get(family_id, family_id.value)
            explanations.append(
                f"{label} proximity suppressed — no explicit {label.lower()} evidence "
                f"on a technical delivery profile."
            )
            sep.contamination_suppressed.append(family_id.value)

    if family_id not in _CONTAMINATION_FAMILIES and proximity > 0.2:
        max_penalty = max(0.0, proximity - 0.18)
        penalty = min(penalty, max_penalty)

    adjusted = round(max(0.0, proximity - penalty), 4)

    own_gate = sep.family_gate_scores.get(family_id.value, 0.0)
    if (
        family_id in _TRANSFORMATION_INFLATION_FAMILIES
        and sep.delivery_governance_dominant
        and max(tpm_gate, release_gate) >= 0.55
        and own_gate < 0.45
    ):
        capped = min(adjusted, 0.14)
        penalty = round(penalty + max(0.0, adjusted - capped), 4)
        adjusted = round(capped, 4)
    if (
        family_id == RoleFamilyId.CLOUD_TRANSFORMATION
        and sep.delivery_governance_dominant
        and release_gate >= 0.55
        and tpm_gate >= 0.35
    ):
        capped = min(adjusted, 0.12)
        penalty = round(penalty + max(0.0, adjusted - capped), 4)
        adjusted = round(capped, 4)
    explanation = " ".join(explanations) if explanations else None
    return adjusted, round(penalty, 4), explanation


ROLE_FAMILY_LABELS: dict[RoleFamilyId, str] = {
    RoleFamilyId.RELEASE_GOVERNANCE: "Release Governance",
    RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT: "Technical Program Management",
    RoleFamilyId.PROGRAM_LEADERSHIP: "Program Leadership",
    RoleFamilyId.ENTERPRISE_DELIVERY: "Enterprise Delivery",
    RoleFamilyId.HR: "HR",
    RoleFamilyId.SALES: "Sales",
    RoleFamilyId.FINANCE: "Finance",
}


def _gate_missing_message(family_id: RoleFamilyId, gate: float) -> str:
    if family_id == RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT:
        return (
            "Candidate demonstrates technical delivery leadership but lacks strong "
            "architecture coordination evidence typical of TPM-heavy roles."
        )
    if family_id == RoleFamilyId.RELEASE_GOVERNANCE:
        return (
            "Limited release-governance evidence (release train, CAB, cutover, or "
            "deployment governance) for a Release Governance track."
        )
    if family_id == RoleFamilyId.PROGRAM_LEADERSHIP:
        return (
            "Delivery and stakeholder language present, but limited PMO, portfolio "
            "governance, or executive program review evidence for Program Leadership."
        )
    if family_id == RoleFamilyId.ENTERPRISE_DELIVERY:
        return (
            "Generic program delivery signals without enterprise rollout, delivery "
            "assurance, or implementation-scale evidence."
        )
    return f"Limited gated evidence ({gate:.0%}) for this role family."


def recruiter_readable_explanation(
    family_id: RoleFamilyId,
    proximity: float,
    dominant: list[str],
    weak: list[str],
    missing: list[str],
    sep: SeparationV2Context | None,
    gate_penalty: float,
) -> str:
    """Recruiter-readable proximity summary (replaces low-quality phrasing)."""
    display = ROLE_FAMILY_LABELS.get(family_id, family_id.value)
    gate = (sep.family_gate_scores.get(family_id.value, 0.0) if sep else 0.0)

    if family_id == RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT and gate < 0.35:
        base = _gate_missing_message(family_id, gate)
    elif gate >= 0.55:
        dom = ", ".join(dominant[:3]) if dominant else "core delivery dimensions"
        base = (
            f"Strong fit for {display} based on gated evidence ({gate:.0%}) "
            f"anchored in {dom}."
        )
    elif proximity >= 0.65:
        base = f"Solid {display} alignment with meaningful capability overlap."
    elif proximity >= 0.45:
        base = f"Moderate {display} alignment with mixed evidence strength."
    else:
        base = f"Limited {display} alignment"

    if missing and family_id != RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT:
        base += f"; gaps in {', '.join(missing[:3])}."
    elif weak and proximity < 0.6:
        base += f"; weaker in {', '.join(weak[:2])}."

    if gate_penalty > 0.15:
        base += f" Separation calibration applied (penalty {gate_penalty:.0%})."

    return base if base.endswith(".") else base + "."
