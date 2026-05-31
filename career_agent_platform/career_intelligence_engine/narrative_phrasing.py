"""Recruiter-grade narrative phrasing — deterministic, no LLM."""

from __future__ import annotations

from career_intelligence_engine.models.job_profile import JobProfile
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.ontology.capability_vectors import DIMENSION_LABELS

# Executive strength phrasing (rotate by dimension hash for variety)
_STRENGTH_TEMPLATES: dict[str, tuple[str, ...]] = {
    "enterprise_governance": (
        "Governance and steering cadence align well with role expectations",
        "Demonstrates credible enterprise governance and program oversight",
        "Portfolio steering and governance rituals are well evidenced",
    ),
    "technical_execution": (
        "Technical delivery coordination is a clear differentiator",
        "Hands-on technical execution depth matches delivery-heavy expectations",
    ),
    "transformation_strategy": (
        "Transformation narrative is visible in documented program outcomes",
        "Strategic transformation ownership appears credible for this profile",
        "Operating-model and change outcomes support transformation-oriented roles",
    ),
    "delivery_execution": (
        "Program delivery outcomes are well represented",
        "Execution track record supports delivery-accountable roles",
    ),
    "release_governance": (
        "Release and SDLC governance experience is well evidenced",
        "Release train and delivery governance depth stand out",
    ),
    "stakeholder_complexity": (
        "Matrix stakeholder leadership reads clearly on the resume",
        "Cross-functional stakeholder scope is well represented",
        "Multi-team stakeholder alignment appears credible for senior scope",
        "Executive and matrix stakeholder coordination are documented",
    ),
    "architecture_coordination": (
        "Architecture coordination and technical alignment are credible",
        "Solution and enterprise architecture coordination appear strong",
    ),
    "portfolio_management": (
        "Portfolio governance and benefits ownership are visible",
        "Portfolio-level prioritization and governance are well represented",
    ),
    "executive_communication": (
        "Executive communication and sponsorship engagement are evidenced",
        "C-suite and steering-forum communication appear credible",
    ),
    "operational_management": (
        "Operational run-state and service management are documented",
        "Run-state operations ownership supports ops-oriented roles",
    ),
    "product_thinking": (
        "Product discovery and roadmap ownership are represented",
        "Customer and product outcomes are visible in the profile",
    ),
    "ai_strategy": (
        "Enterprise AI strategy and adoption themes are present",
        "AI program ownership signals align with transformation-oriented roles",
    ),
    "change_management": (
        "Organizational change and adoption outcomes are documented",
        "Change leadership and adoption metrics are represented",
    ),
    "organizational_leadership": (
        "Org leadership and team-scale accountability are evidenced",
        "People and organizational leadership depth supports senior scope",
    ),
    "engineering_depth": (
        "Engineering depth supports technical credibility with delivery teams",
        "Platform and engineering coordination depth are visible",
    ),
}

_GAP_STRATEGIC: dict[str, str] = {
    "transformation_strategy": (
        "Strategic transformation ownership appears less emphasized than "
        "execution governance and operational delivery"
    ),
    "ai_strategy": (
        "Enterprise AI strategy ownership is not yet a primary narrative "
        "compared with core program delivery strengths"
    ),
    "product_thinking": (
        "Product roadmap and customer-outcome ownership are underrepresented "
        "relative to program and governance strengths"
    ),
    "operational_management": (
        "Run-state operations and service-management ownership are lighter "
        "than program-delivery evidence"
    ),
    "architecture_coordination": (
        "Architecture review and solution-alignment ownership are not yet "
        "a headline theme in the profile"
    ),
    "engineering_depth": (
        "Hands-on engineering depth is thinner than coordination and "
        "governance-oriented strengths"
    ),
    "release_governance": (
        "Release train and SDLC governance are less prominent than general "
        "delivery and stakeholder leadership"
    ),
    "executive_communication": (
        "Executive sponsorship and board-level communication could be "
        "surfaced more explicitly"
    ),
    "change_management": (
        "Organizational change and adoption outcomes are less visible than "
        "delivery and governance themes"
    ),
}

_DEFAULT_GAP = (
    "{label} is required at a higher level than currently evidenced "
    "in the profile"
)

_RESUME_IMPROVEMENTS: dict[str, str] = {
    "product": (
        "Emphasize product roadmap ownership, customer discovery, and "
        "go-to-market outcomes with quantified adoption or revenue impact."
    ),
    "operations": (
        "Surface run-state operations, SLA/incident management, and "
        "production support ownership with service-level metrics."
    ),
    "architecture": (
        "Call out architecture review board participation, solution "
        "alignment, or enterprise architecture coordination with named scope."
    ),
    "ai_transformation": (
        "Lead with enterprise AI strategy, operating-model redesign, and "
        "transformation KPIs—not only pilot delivery."
    ),
    "release_governance": (
        "Highlight release train, PI planning, and SDLC governance ownership "
        "with cadence and quality metrics."
    ),
    "consulting_pmo": (
        "Emphasize cross-functional governance and transformation coordination "
        "outcomes for consulting-oriented PMO roles."
    ),
    "gate_failure": (
        "Address role-critical eligibility gaps with explicit ownership "
        "evidence before applying."
    ),
}

ROLE_FAMILY_RESUME_HINT: dict[RoleFamilyId, str] = {
    RoleFamilyId.PROGRAM_LEADERSHIP: (
        "Position portfolio governance, benefits realization, and executive "
        "steering outcomes ahead of tactical task lists."
    ),
    RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT: (
        "Lead with technical delivery coordination, release governance, and "
        "architecture alignment—not only status reporting."
    ),
    RoleFamilyId.AI_PROGRAM_MANAGEMENT: (
        "Foreground AI portfolio governance, responsible AI adoption, and "
        "cross-functional AI delivery metrics."
    ),
    RoleFamilyId.AI_TRANSFORMATION: (
        "Anchor the summary in transformation roadmaps, operating-model "
        "change, and measurable adoption—not tool familiarity."
    ),
    RoleFamilyId.RELEASE_GOVERNANCE: (
        "Prioritize release train, deployment governance, and quality "
        "metrics in the top third of the resume."
    ),
    RoleFamilyId.PRODUCT_MANAGEMENT: (
        "Open with customer outcomes, roadmap decisions, and discovery "
        "evidence—not program mechanics alone."
    ),
    RoleFamilyId.OPERATIONS: (
        "Lead with operational reliability, incident reduction, and "
        "service-management accountability."
    ),
}


def _pick_template(key: str, templates: tuple[str, ...]) -> str:
    if not templates:
        return ""
    return templates[hash(key) % len(templates)]


def phrase_strength(dim: str, contrib: float, *, context: str = "") -> str:
    """Recruiter-readable strength line without job-weight percentages."""
    templates = _STRENGTH_TEMPLATES.get(dim)
    if templates:
        pick_key = f"{dim}:{context}" if context else dim
        return _pick_template(pick_key, templates)
    label = DIMENSION_LABELS.get(dim, dim.replace("_", " ").title())
    if contrib >= 0.12:
        return f"{label} is a credible fit for this role"
    return f"{label} contributes positively to overall fit"


def phrase_gap(dim: str, cand_val: float, job_weight: float, *, context: str = "") -> str:
    """Strategic gap wording — avoids mechanical score comparisons in UX."""
    label = DIMENSION_LABELS.get(dim, dim.replace("_", " ").title())
    strategic = _GAP_STRATEGIC.get(dim)
    if strategic:
        variants = (strategic,)
        if dim == "transformation_strategy":
            variants = (
                strategic,
                "Transformation ownership appears less central than delivery and governance themes",
                "Strategic change narrative is thinner than execution evidence",
            )
        elif dim == "release_governance":
            variants = (
                strategic,
                "Release train and SDLC governance are less prominent than general delivery themes",
                "PI planning and release governance depth trail program-delivery emphasis",
            )
        pick_key = f"gap:{dim}:{context}" if context else f"gap:{dim}"
        return _pick_template(pick_key, variants)
    if job_weight >= 0.35 and cand_val < 0.15:
        return (
            f"Role expects stronger {label.lower()} ownership than the profile "
            "currently foregrounds"
        )
    return _DEFAULT_GAP.format(label=label)


def phrase_missing_capability(item: str) -> str:
    """Humanize engine-generated missing-capability strings."""
    cleaned = item.strip()
    lower = cleaned.lower()
    if "job requires" in lower and "candidate shows" in lower:
        for dim_id, label in DIMENSION_LABELS.items():
            if label.lower() in lower:
                return phrase_gap(dim_id, 0.0, 0.25)
        return cleaned.split(":")[0] if ":" in cleaned else cleaned
    if lower.startswith("gap dimension:"):
        dim = cleaned.split(":", 1)[-1].strip()
        return phrase_gap(dim, 0.0, 0.25)
    return cleaned


def interpret_profile_pattern(
    dominant_dims: list[str],
    weak_dims: list[str],
    job: JobProfile,
) -> str:
    """One-sentence strategic read of capability pattern vs role."""
    dom_labels = [DIMENSION_LABELS.get(d, d) for d in dominant_dims[:3]]
    weak_labels = [DIMENSION_LABELS.get(d, d) for d in weak_dims[:2]]

    family = job.primary_role_family.value.replace("_", " ")
    if dom_labels and weak_labels:
        variants = (
            (
                f"Strongest signal: {dom_labels[0].lower()} and {dom_labels[1].lower() if len(dom_labels) > 1 else 'delivery'}; "
                f"{weak_labels[0].lower()} is lighter for {family} scope."
            ),
            (
                f"Resume emphasizes {', '.join(d.lower() for d in dom_labels[:2])}; "
                f"{weak_labels[0].lower()} is not yet a headline theme."
            ),
        )
        pick_key = f"{job.primary_role_family}:{job.title or ''}:{','.join(dominant_dims[:2])}"
        return variants[hash(pick_key) % len(variants)]
    if dom_labels:
        return f"Evidence clusters around {dom_labels[0].lower()} and adjacent delivery themes."
    return ""


def compose_positioning_summary(
    *,
    job_display: str,
    score: float,
    gate_passed: bool,
    gate_reason: str,
    dominant_dims: list[str],
    weak_dims: list[str],
    strategic_pattern: str,
) -> str:
    """Executive positioning paragraph — concise, recruiter-grade."""
    if not gate_passed:
        reason = gate_reason or "Missing role-critical ownership evidence."
        return (
            f"Not recommended for shortlist on this {job_display} role: "
            f"{reason.rstrip('.')}."
        )

    if score >= 0.78:
        tier = f"Shortlist-ready for {job_display}; capability themes match role priorities."
    elif score >= 0.58:
        tier = f"Selective fit for {job_display}; strengths land with addressable gaps."
    else:
        tier = f"Below shortlist bar for {job_display}; role-critical gaps remain."

    if strategic_pattern:
        return f"{tier} {strategic_pattern}"
    return tier


def resume_improvements_for_job(
    job: JobProfile,
    *,
    gate_failed: bool,
    product_low: bool,
    ops_low: bool,
    arch_low: bool,
) -> list[str]:
    """Role-aware resume guidance — specific and non-template-heavy."""
    out: list[str] = []
    if gate_failed:
        out.append(_RESUME_IMPROVEMENTS["gate_failure"])

    family_hint = ROLE_FAMILY_RESUME_HINT.get(job.primary_role_family)
    if family_hint:
        out.append(family_hint)

    if job.is_product_heavy and product_low:
        out.append(_RESUME_IMPROVEMENTS["product"])
    if job.is_operations_heavy and ops_low:
        out.append(_RESUME_IMPROVEMENTS["operations"])
    if job.is_architecture_heavy and arch_low:
        out.append(_RESUME_IMPROVEMENTS["architecture"])
    if job.is_ai_transformation:
        out.append(_RESUME_IMPROVEMENTS["ai_transformation"])
    if job.is_release_governance_heavy:
        out.append(_RESUME_IMPROVEMENTS["release_governance"])

    if job.primary_role_family in (
        RoleFamilyId.PROGRAM_LEADERSHIP,
        RoleFamilyId.ENTERPRISE_DELIVERY,
    ):
        out.append(_RESUME_IMPROVEMENTS["consulting_pmo"])

    seen: set[str] = set()
    deduped: list[str] = []
    for line in out:
        key = line.lower()[:50]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(line)
    return deduped[:5]
