"""
First-class job identity layer — deterministic recruiter-grade entities.

Downstream consumers: recommendations, workspace, dashboard, routing,
market intelligence, analytics, follow-up tracking, future automation.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from career_intelligence_engine.ontology.capability_vectors import DIMENSION_LABELS
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES
from career_intelligence_engine.models.ontology import RoleFamilyId
from job_sources.company_registry import resolve_company
from job_sources.industry_mapper import infer_industry, industry_chip_label
from job_sources.job_posting import JobPosting
from job_sources.location_inference import infer_location, location_display_line
from job_sources.title_normalization import is_noisy_title, normalize_title
from recommendation_engine import RecommendationResult

ENTITY_VERSION = "2"

_SKILL_KEYWORDS: tuple[tuple[str, str], ...] = (
    (r"\brelease governance\b|\brelease train\b|\bpi planning\b", "Release Governance"),
    (r"\benterprise delivery\b|\bprogram delivery\b", "Enterprise Delivery"),
    (r"\bai/ml\b|\bgenai\b|\blarge language model\b|\brag\b", "AI/ML Programs"),
    (r"\bllm evaluation\b|\bmodel evaluation\b", "LLM Evaluation"),
    (r"\barchitecture\b|\benterprise architect\b", "Architecture Ownership"),
    (r"\bstakeholder management\b|\bexecutive steering\b", "Stakeholder Alignment"),
    (r"\bmlops\b|\bmodel lifecycle\b", "MLOps"),
    (r"\bworkflow automation\b|\bprocess automation\b", "Workflow Automation"),
    (r"\bcloud migration\b|\bcloud transformation\b", "Cloud Transformation"),
    (r"\bgovernance\b|\bcompliance\b|\baudit\b", "Governance"),
)

_INTENSITY_SIGNALS: dict[str, tuple[str, ...]] = {
    "governance_requirements": (
        r"\bgovernance\b",
        r"\bcompliance\b",
        r"\brelease train\b",
        r"\bsteering committee\b",
    ),
    "ai_maturity_signal": (
        r"\bgenai\b",
        r"\bllm\b",
        r"\bmlops\b",
        r"\bresponsible ai\b",
    ),
    "architecture_depth": (
        r"\barchitecture\b",
        r"\btechnical design\b",
        r"\bplatform architecture\b",
    ),
    "transformation_intensity": (
        r"\btransformation\b",
        r"\boperating model\b",
        r"\badoption\b",
        r"\bchange management\b",
    ),
}


@dataclass
class NormalizedJobPosting:
    """Persistent recruiter-grade job identity."""

    job_id: str
    normalized_title: str
    raw_title: str
    company_name: str
    company_aliases: list[str] = field(default_factory=list)
    inferred_industry: str = "Enterprise Technology"
    inferred_role_family: str = "enterprise_delivery"
    inferred_seniority: str = "Senior"
    inferred_leadership_level: str = "individual_contributor"
    inferred_company_type: str = "Global Enterprise"
    location: str = "Location Flexible"
    remote_type: str = "Flexible"
    employment_type: str = "Full-time"
    source: str = "Imported JD"
    salary_range: str = ""
    confidence: float = 0.0
    recruiter_name: str = ""
    recruiter_contact: str = ""
    clean_display_label: str = ""
    recommendation_label: str = ""
    normalized_summary: str = ""
    top_required_skills: list[str] = field(default_factory=list)
    top_matching_dimensions: list[str] = field(default_factory=list)
    top_missing_dimensions: list[str] = field(default_factory=list)
    governance_requirements: str = "Low"
    ai_maturity_signal: str = "Low"
    architecture_depth: str = "Low"
    transformation_intensity: str = "Low"
    entity_version: str = ENTITY_VERSION

    # Backward-compatible accessors
    @property
    def clean_title(self) -> str:
        return self.normalized_title

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["clean_title"] = self.normalized_title  # legacy consumers
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "NormalizedJobPosting":
        title = str(
            data.get("normalized_title")
            or data.get("clean_title")
            or "Enterprise Program Leadership Opportunity",
        )
        return cls(
            job_id=str(data.get("job_id") or ""),
            normalized_title=title,
            raw_title=str(data.get("raw_title") or data.get("raw_title", "")),
            company_name=str(data.get("company_name") or "Enterprise Technology Organization"),
            company_aliases=list(data.get("company_aliases") or []),
            inferred_industry=str(data.get("inferred_industry") or "Enterprise Technology"),
            inferred_role_family=str(data.get("inferred_role_family") or "enterprise_delivery"),
            inferred_seniority=str(data.get("inferred_seniority") or "Senior"),
            inferred_leadership_level=str(data.get("inferred_leadership_level") or "individual_contributor"),
            inferred_company_type=str(data.get("inferred_company_type") or "Global Enterprise"),
            location=str(data.get("location") or "Location Flexible"),
            remote_type=str(data.get("remote_type") or "Flexible"),
            employment_type=str(data.get("employment_type") or "Full-time"),
            source=str(data.get("source") or "Imported JD"),
            salary_range=str(data.get("salary_range") or ""),
            confidence=float(data.get("confidence") or 0.0),
            recruiter_name=str(data.get("recruiter_name") or ""),
            recruiter_contact=str(data.get("recruiter_contact") or ""),
            clean_display_label=str(data.get("clean_display_label") or ""),
            recommendation_label=str(data.get("recommendation_label") or ""),
            normalized_summary=str(data.get("normalized_summary") or ""),
            top_required_skills=list(data.get("top_required_skills") or []),
            top_matching_dimensions=list(data.get("top_matching_dimensions") or []),
            top_missing_dimensions=list(data.get("top_missing_dimensions") or []),
            governance_requirements=str(data.get("governance_requirements") or "Low"),
            ai_maturity_signal=str(data.get("ai_maturity_signal") or "Low"),
            architecture_depth=str(data.get("architecture_depth") or "Low"),
            transformation_intensity=str(data.get("transformation_intensity") or "Low"),
            entity_version=str(data.get("entity_version") or ENTITY_VERSION),
        )


def _search_skills(raw_text: str) -> list[str]:
    low = raw_text.lower()
    found: list[str] = []
    for pattern, label in _SKILL_KEYWORDS:
        if re.search(pattern, low) and label not in found:
            found.append(label)
    return found[:8]


def _intensity_label(raw_text: str, patterns: tuple[str, ...]) -> str:
    hits = sum(1 for p in patterns if re.search(p, raw_text, re.I))
    if hits >= 3:
        return "High"
    if hits >= 1:
        return "Medium"
    return "Low"


def _humanize_dimensions(keys: list[str]) -> list[str]:
    out: list[str] = []
    for key in keys:
        out.append(DIMENSION_LABELS.get(key, key.replace("_", " ").title()))
    return out


def _role_family_display(role_family: str) -> str:
    try:
        return ROLE_FAMILIES[RoleFamilyId(role_family)].display_name
    except (ValueError, KeyError):
        return role_family.replace("_", " ").title()


def _infer_employment_type(raw_text: str) -> str:
    low = raw_text.lower()
    if "contract" in low or "contractor" in low:
        return "Contract"
    if "part-time" in low or "part time" in low:
        return "Part-time"
    return "Full-time"


def _infer_salary_range(raw_text: str) -> str:
    match = re.search(
        r"(?:\$|₹|rs\.?|inr|usd)\s?[\d,.]+(?:\s?[-–]\s?(?:\$|₹|rs\.?|inr|usd)?\s?[\d,.]+)?",
        raw_text,
        re.I,
    )
    if match:
        return match.group(0).strip()
    if re.search(r"\bcompetitive compensation\b|\battractive package\b", raw_text, re.I):
        return "Competitive package"
    return ""


def _infer_recruiter(raw_text: str) -> tuple[str, str]:
    name_match = re.search(
        r"(?:recruiter|talent partner|hiring manager)\s*[:\-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        raw_text,
    )
    contact_match = re.search(
        r"([\w.+-]+@[\w.-]+\.\w+)|(\+?\d[\d\s\-().]{8,}\d)",
        raw_text,
    )
    name = name_match.group(1).strip() if name_match else ""
    contact = ""
    if contact_match:
        contact = contact_match.group(1) or contact_match.group(2) or ""
    return name, contact.strip()


def _compute_confidence(
    *,
    explicit_company: bool,
    explicit_title: bool,
    explicit_location: bool,
    skills_found: int,
) -> float:
    score = 0.45
    if explicit_company:
        score += 0.15
    if explicit_title:
        score += 0.15
    if explicit_location:
        score += 0.10
    score += min(0.15, skills_found * 0.03)
    return round(min(0.95, score), 3)


def build_normalized_summary(entity: NormalizedJobPosting) -> str:
    family = _role_family_display(entity.inferred_role_family)
    industry = industry_chip_label(entity.inferred_industry)
    loc_line = location_display_line(entity.location, entity.remote_type)
    skills = ", ".join(entity.top_required_skills[:3]) if entity.top_required_skills else "cross-functional delivery"

    templates = {
        "ai_transformation": (
            f"This role emphasizes enterprise AI delivery, transformation governance, and {family} "
            f"leadership in a {industry.lower()} environment ({loc_line}). "
            f"Key themes include {skills}."
        ),
        "release_governance": (
            f"This role emphasizes release governance, agile-at-scale coordination, and {family} "
            f"accountability within a {industry.lower()} organization ({loc_line}). "
            f"Critical skills: {skills}."
        ),
        "technical_program_management": (
            f"This role emphasizes cross-functional technical delivery, architecture alignment, and "
            f"{family} leadership in a {industry.lower()} setting ({loc_line}). "
            f"Priority skills: {skills}."
        ),
    }
    template = templates.get(
        entity.inferred_role_family,
        (
            f"This role emphasizes {family}, enterprise delivery, and stakeholder leadership "
            f"in a {industry.lower()} environment ({loc_line}). "
            f"Core requirements: {skills}."
        ),
    )
    return template


def build_display_labels(entity: NormalizedJobPosting) -> tuple[str, str]:
    loc_line = location_display_line(entity.location, entity.remote_type)
    display = f"{entity.normalized_title} @ {entity.company_name}"
    rec_label = f"{entity.normalized_title} — {entity.company_name}"
    if loc_line and loc_line not in {"Location Flexible"}:
        rec_label = f"{rec_label} · {loc_line}"
    return display, rec_label


def build_job_entity(
    *,
    job_id: str,
    raw_title: str,
    company: str,
    location: str,
    raw_text: str,
    source: str,
    role_family_hint: str = "",
    top_matching_dimensions: list[str] | None = None,
    top_missing_dimensions: list[str] | None = None,
) -> NormalizedJobPosting:
    """Core entity builder — single entry point for all normalization."""
    raw = raw_text or ""
    explicit_company = not is_noisy_title(company) if company else False
    explicit_title = not is_noisy_title(raw_title) if raw_title else False

    company_name, aliases, company_type = resolve_company(
        company=company,
        raw_text=raw,
        title=raw_title,
    )
    title_result = normalize_title(
        title=raw_title,
        raw_text=raw,
        role_family_hint=role_family_hint,
    )
    loc_result = infer_location(location=location, raw_text=raw)
    explicit_location = bool(location and not is_noisy_title(location))

    industry = infer_industry(
        company_type=company_type,
        company_name=company_name,
        raw_text=raw,
    )
    skills = _search_skills(raw)
    recruiter_name, recruiter_contact = _infer_recruiter(raw)

    entity = NormalizedJobPosting(
        job_id=job_id,
        normalized_title=title_result.normalized_title,
        raw_title=title_result.raw_title or raw_title,
        company_name=company_name,
        company_aliases=aliases,
        inferred_industry=industry,
        inferred_role_family=title_result.inferred_role_family,
        inferred_seniority=title_result.inferred_seniority,
        inferred_leadership_level=title_result.inferred_leadership_level,
        inferred_company_type=company_type,
        location=loc_result.location,
        remote_type=loc_result.remote_type,
        employment_type=_infer_employment_type(raw),
        source=source if source and source.lower() != "unknown" else "Imported JD",
        salary_range=_infer_salary_range(raw),
        confidence=_compute_confidence(
            explicit_company=explicit_company,
            explicit_title=explicit_title,
            explicit_location=explicit_location,
            skills_found=len(skills),
        ),
        recruiter_name=recruiter_name,
        recruiter_contact=recruiter_contact,
        top_required_skills=skills,
        top_matching_dimensions=_humanize_dimensions(top_matching_dimensions or [])[:6],
        top_missing_dimensions=_humanize_dimensions(top_missing_dimensions or [])[:6],
        governance_requirements=_intensity_label(raw, _INTENSITY_SIGNALS["governance_requirements"]),
        ai_maturity_signal=_intensity_label(raw, _INTENSITY_SIGNALS["ai_maturity_signal"]),
        architecture_depth=_intensity_label(raw, _INTENSITY_SIGNALS["architecture_depth"]),
        transformation_intensity=_intensity_label(raw, _INTENSITY_SIGNALS["transformation_intensity"]),
    )
    entity.normalized_summary = build_normalized_summary(entity)
    entity.clean_display_label, entity.recommendation_label = build_display_labels(entity)
    return entity


def normalize_job_posting(posting: JobPosting) -> NormalizedJobPosting:
    profile = posting.parsed_job_profile
    hint = profile.primary_role_family.value if profile else ""
    return build_job_entity(
        job_id=posting.job_id,
        raw_title=posting.title,
        company=posting.company,
        location=posting.location,
        raw_text=posting.raw_text,
        source=posting.source,
        role_family_hint=hint,
    )


def normalize_recommendation(
    rec: RecommendationResult,
    *,
    raw_text: str = "",
    posting: JobPosting | None = None,
) -> NormalizedJobPosting:
    detail = rec.match_detail or {}
    role_family = str(detail.get("primary_role_family") or "")
    raw = raw_text or (posting.raw_text if posting else "")
    return build_job_entity(
        job_id=rec.job_id,
        raw_title=rec.job_title,
        company=rec.company,
        location=str(detail.get("location") or (posting.location if posting else "")),
        raw_text=raw,
        source=rec.source,
        role_family_hint=role_family,
        top_matching_dimensions=list(rec.dominant_dimensions or []),
        top_missing_dimensions=list(rec.missing_dimensions or []),
    )


def apply_normalization_to_recommendation(
    rec: RecommendationResult,
    *,
    raw_text: str = "",
    posting: JobPosting | None = None,
) -> NormalizedJobPosting:
    """Attach entity to recommendation; does not change match scores."""
    entity = normalize_recommendation(rec, raw_text=raw_text, posting=posting)
    rec.job_title = entity.normalized_title
    rec.company = entity.company_name
    detail = dict(rec.match_detail or {})
    detail["normalized"] = entity.to_dict()
    detail["job_entity"] = entity.to_dict()
    detail["location"] = entity.location
    detail["remote_type"] = entity.remote_type
    detail["inferred_industry"] = entity.inferred_industry
    detail["inferred_seniority"] = entity.inferred_seniority
    detail["clean_display_label"] = entity.clean_display_label
    if not detail.get("primary_role_family"):
        detail["primary_role_family"] = entity.inferred_role_family
    rec.match_detail = detail
    return entity


def normalized_from_recommendation(rec: RecommendationResult) -> NormalizedJobPosting:
    detail = rec.match_detail or {}
    cached = detail.get("job_entity") or detail.get("normalized")
    if cached:
        return NormalizedJobPosting.from_dict(cached)
    return normalize_recommendation(rec)


def pretty_job_label(
    *,
    title: str | None = None,
    company: str | None = None,
    location: str | None = None,
    normalized: Mapping[str, Any] | NormalizedJobPosting | None = None,
) -> str:
    if normalized is not None:
        if isinstance(normalized, NormalizedJobPosting):
            if normalized.clean_display_label:
                return normalized.clean_display_label
            data = normalized.to_dict()
        else:
            data = dict(normalized)
        if data.get("clean_display_label"):
            return str(data["clean_display_label"])
        if data.get("recommendation_label"):
            return str(data["recommendation_label"]).split(" · ")[0].replace(" — ", " @ ")
        title = data.get("normalized_title") or data.get("clean_title") or title
        company = data.get("company_name") or company
        location = data.get("location") or location

    entity = build_job_entity(
        job_id="display",
        raw_title=str(title or ""),
        company=str(company or ""),
        location=str(location or ""),
        raw_text="",
        source="display",
    )
    return entity.clean_display_label


# Legacy thin wrappers — delegate to entity layer
def infer_company(*, company: str, raw_text: str, title: str = "") -> str:
    name, _, _ = resolve_company(company=company, raw_text=raw_text, title=title)
    return name


def infer_title(*, title: str, raw_text: str, role_family: str = "") -> str:
    return normalize_title(title=title, raw_text=raw_text, role_family_hint=role_family).normalized_title


def infer_location_legacy(*, location: str, raw_text: str) -> str:
    return infer_location(location=location, raw_text=raw_text).location


def infer_industry_legacy(raw_text: str) -> str:
    return infer_industry(company_type="", company_name="", raw_text=raw_text)


def infer_seniority(*, title: str, raw_text: str) -> str:
    from job_sources.title_normalization import infer_seniority as _sen

    return _sen(title=title, raw_text=raw_text)


def infer_remote_type(*, location: str, raw_text: str) -> str:
    from job_sources.location_inference import infer_remote_type as _remote

    return _remote(location=location, raw_text=raw_text)


def infer_employment_type(raw_text: str) -> str:
    return _infer_employment_type(raw_text)


def infer_salary_range(raw_text: str) -> str:
    return _infer_salary_range(raw_text)


def infer_recruiter_name(raw_text: str) -> str:
    return _infer_recruiter(raw_text)[0]


def persist_entity_snapshot(entity: NormalizedJobPosting) -> dict[str, Any]:
    """Canonical JSON shape for queue, packages, tracker, analytics."""
    return entity.to_dict()
