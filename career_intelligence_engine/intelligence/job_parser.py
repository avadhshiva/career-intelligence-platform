"""Deterministic job description parser — structured JobProfile output."""

from __future__ import annotations

import re
from dataclasses import dataclass

from career_intelligence_engine.intelligence.capability_density import score_text_for_family
from career_intelligence_engine.intelligence.seniority_inference import SeniorityInference
from career_intelligence_engine.intelligence.transformation_inference import (
    TransformationInference,
)
from career_intelligence_engine.models.job_profile import JobProfile
from career_intelligence_engine.models.ontology import (
    AIMaturity,
    EnterpriseExposure,
    LeadershipLevel,
    ParsedResume,
    RoleFamilyId,
    SeniorityLevel,
)
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES

_SECTION_HEADERS = re.compile(
    r"^(responsibilities|requirements|qualifications|about the role|"
    r"what you will do|key responsibilities|role overview)\s*:?\s*$",
    re.I | re.M,
)

_CLOUD_PATTERNS = [
    re.compile(r"\b(aws|amazon web services|azure|gcp|google cloud)\b", re.I),
    re.compile(r"\b(kubernetes|k8s|terraform|cloud migration|multi-cloud)\b", re.I),
    re.compile(r"\b(saas|paas|iaas|cloud platform|cloud native)\b", re.I),
]

_ARCH_PATTERNS = [
    re.compile(
        r"\b(enterprise architecture|solution architecture|architecture review|"
        r"architecture board|design authority|technical architecture)\b",
        re.I,
    ),
]

_PRODUCT_PATTERNS = [
    re.compile(
        r"\b(product roadmap|roadmap ownership|product owner|product strategy|"
        r"backlog ownership|customer discovery|product-market fit)\b",
        re.I,
    ),
]

_OPS_PATTERNS = [
    re.compile(
        r"\b(run operations|operational continuity|sla management|incident management|"
        r"production support|it operations|service operations|noc)\b",
        re.I,
    ),
]

_GOVERNANCE_PATTERNS = [
    re.compile(
        r"\b(governance|steering committee|portfolio governance|compliance|"
        r"sox|gdpr|benefits realization|program governance)\b",
        re.I,
    ),
]

_ENTERPRISE_PATTERNS = [
    re.compile(
        r"\b(fortune 500|global enterprise|multi-region|matrix organization|"
        r"enterprise-wide|cross-bu|regulated industry)\b",
        re.I,
    ),
]

_LEADERSHIP_PATTERNS: list[tuple[re.Pattern[str], LeadershipLevel, float]] = [
    (re.compile(r"\b(people manager|direct reports|headcount|org leader)\b", re.I), LeadershipLevel.PEOPLE_MANAGER, 0.9),
    (re.compile(r"\b(executive sponsor|c-suite|board|vp |vice president)\b", re.I), LeadershipLevel.EXECUTIVE, 0.95),
    (re.compile(r"\b(cross-functional lead|team lead|matrix lead)\b", re.I), LeadershipLevel.TEAM_LEAD, 0.75),
    (re.compile(r"\b(individual contributor|hands-on|ic role)\b", re.I), LeadershipLevel.INDIVIDUAL_CONTRIBUTOR, 0.85),
]

_TRANSFORMATION_TYPES: list[tuple[str, re.Pattern[str]]] = [
    ("ai", re.compile(r"\b(ai transformation|genai|enterprise ai|machine learning strategy)\b", re.I)),
    ("cloud", re.compile(r"\b(cloud transformation|cloud migration|platform modernization)\b", re.I)),
    ("digital", re.compile(r"\b(digital transformation|digitization)\b", re.I)),
    ("operating_model", re.compile(r"\b(operating model|target operating model|org redesign)\b", re.I)),
]


@dataclass
class ParsedJobDescription:
    """Intermediate parse result before vector enrichment."""

    raw_text: str
    title: str | None
    bullets: list[str]
    sections: dict[str, str]


def _extract_title(text: str) -> str | None:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return None
    first = lines[0]
    if len(first) < 120 and not first.lower().startswith(("responsibilities", "requirements")):
        if re.search(r"\b(manager|director|lead|engineer|program|product|operations|architect)\b", first, re.I):
            return first
    for line in lines[:5]:
        if re.search(
            r"\b(manager|director|lead|engineer|program|product|operations|architect|tpm)\b",
            line,
            re.I,
        ):
            return line[:120]
    return lines[0][:120] if lines else None


def _extract_bullets(text: str) -> list[str]:
    bullets: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^[\-\*•]\s+", stripped) or re.match(r"^\d+[\.\)]\s+", stripped):
            bullet = re.sub(r"^[\-\*•\d\.\)]\s+", "", stripped).strip()
            if len(bullet) > 10:
                bullets.append(bullet)
    return bullets


def _split_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {"body": text}
    for match in _SECTION_HEADERS.finditer(text):
        header = match.group(1).lower().replace(" ", "_")
        start = match.end()
        next_match = _SECTION_HEADERS.search(text, start)
        end = next_match.start() if next_match else len(text)
        sections[header] = text[start:end].strip()
    return sections


def _pattern_density(corpus: str, patterns: list[re.Pattern[str]]) -> float:
    hits = sum(len(p.findall(corpus)) for p in patterns)
    if hits == 0:
        return 0.0
    if hits >= 4:
        return 0.9
    if hits >= 2:
        return 0.65
    return 0.35


def _infer_role_families(corpus: str, bullets: list[str], title: str | None) -> tuple[RoleFamilyId, list[RoleFamilyId], dict[str, float]]:
    scores: dict[RoleFamilyId, float] = {}
    for family_id, defn in ROLE_FAMILIES.items():
        score = score_text_for_family(
            corpus,
            bullets,
            defn.positive_signals or defn.title_signals,
            defn.negative_signals,
        )
        if title:
            title_lower = title.lower()
            for sig in defn.title_signals:
                if sig.lower() in title_lower:
                    score += 8.0
            if defn.canonical_name and defn.canonical_name.lower() in title_lower:
                score += 5.0
        scores[family_id] = score

    ranked = sorted(scores.items(), key=lambda x: -x[1])
    primary = ranked[0][0] if ranked else RoleFamilyId.ENTERPRISE_DELIVERY
    candidates = [fid for fid, _ in ranked[:5] if scores[fid] > 0]
    if primary not in candidates:
        candidates.insert(0, primary)
    return primary, candidates[:5], {k.value: round(v, 2) for k, v in scores.items()}


def _infer_seniority(corpus: str, title: str | None) -> SeniorityLevel:
    fake_resume = ParsedResume(
        raw_text=corpus,
        job_titles=[title] if title else [],
        bullets=[],
    )
    result = SeniorityInference().infer(fake_resume)
    return result.level


def _infer_leadership(corpus: str) -> LeadershipLevel:
    scores: dict[LeadershipLevel, float] = {lvl: 0.0 for lvl in LeadershipLevel}
    for pattern, level, weight in _LEADERSHIP_PATTERNS:
        if pattern.search(corpus):
            scores[level] += weight
    best = max(scores.items(), key=lambda x: x[1])
    return best[0] if best[1] > 0 else LeadershipLevel.UNKNOWN


def _infer_enterprise_scale(corpus: str) -> EnterpriseExposure:
    hits = sum(len(p.findall(corpus)) for p in _ENTERPRISE_PATTERNS)
    if hits >= 3:
        return EnterpriseExposure.DEEP
    if hits >= 2:
        return EnterpriseExposure.STRONG
    if hits >= 1:
        return EnterpriseExposure.MODERATE
    return EnterpriseExposure.LIMITED


def _infer_transformation_type(corpus: str) -> str:
    for label, pattern in _TRANSFORMATION_TYPES:
        if pattern.search(corpus):
            return label
    return "none"


def _infer_cloud_indicators(corpus: str) -> list[str]:
    found: list[str] = []
    for pattern in _CLOUD_PATTERNS:
        for match in pattern.findall(corpus):
            token = match if isinstance(match, str) else match[0]
            token = token.strip().lower()
            if token and token not in found:
                found.append(token)
    return found[:8]


def _classify_job_heavy_flags(
    primary: RoleFamilyId,
    raw_scores: dict[str, float],
    corpus: str,
    title: str | None,
) -> dict[str, bool]:
    title_lower = (title or "").lower()
    product_raw = raw_scores.get("product_thinking", 0.0)
    ops_raw = raw_scores.get("operational_management", 0.0)
    arch_raw = raw_scores.get("architecture_coordination", 0.0)
    release_raw = raw_scores.get("release_governance", 0.0)
    ai_raw = raw_scores.get("ai_strategy", 0.0)
    trans_raw = raw_scores.get("transformation_strategy", 0.0)

    product_pat = _pattern_density(corpus, _PRODUCT_PATTERNS)
    ops_pat = _pattern_density(corpus, _OPS_PATTERNS)

    is_product = (
        primary in (RoleFamilyId.PRODUCT_MANAGEMENT, RoleFamilyId.PRODUCT_DELIVERY)
        or product_raw >= 0.25
        or product_pat >= 0.65
        or "product" in title_lower
    )
    is_ops = (
        primary in (RoleFamilyId.OPERATIONS, RoleFamilyId.ENTERPRISE_OPERATIONS)
        or ops_raw >= 0.25
        or ops_pat >= 0.65
        or "operations" in title_lower
    )
    is_arch = (
        primary
        in (
            RoleFamilyId.ENTERPRISE_ARCHITECTURE_DELIVERY,
            RoleFamilyId.SOFTWARE_ENGINEERING,
            RoleFamilyId.PLATFORM_MODERNIZATION,
        )
        or arch_raw >= 0.30
        or "architect" in title_lower
    )
    is_release = (
        primary == RoleFamilyId.RELEASE_GOVERNANCE
        or release_raw >= 0.35
        or "release" in title_lower
    )
    is_ai_trans = (
        primary in (RoleFamilyId.AI_TRANSFORMATION, RoleFamilyId.AI_GOVERNANCE)
        or (ai_raw >= 0.30 and trans_raw >= 0.25)
        or "ai transformation" in corpus
    )
    return {
        "is_product_heavy": is_product,
        "is_operations_heavy": is_ops,
        "is_architecture_heavy": is_arch,
        "is_release_governance_heavy": is_release,
        "is_ai_transformation": is_ai_trans,
    }


class JobDescriptionParser:
    """Parse raw JD text into a structured JobProfile."""

    def parse(self, text: str) -> JobProfile:
        return parse_job_description(text)


def parse_job_description(text: str) -> JobProfile:
    """End-to-end deterministic JD parse."""
    raw = text.strip()
    title = _extract_title(raw)
    bullets = _extract_bullets(raw)
    sections = _split_sections(raw)
    corpus = "\n".join([raw] + bullets).lower()

    primary, candidates, family_scores = _infer_role_families(corpus, bullets, title)
    required_seniority = _infer_seniority(corpus, title)
    leadership_scope = _infer_leadership(corpus)
    enterprise_scale = _infer_enterprise_scale(corpus)
    transformation_type = _infer_transformation_type(corpus)
    cloud_indicators = _infer_cloud_indicators(corpus)
    governance_intensity = _pattern_density(corpus, _GOVERNANCE_PATTERNS)

    product_required = max(
        _pattern_density(corpus, _PRODUCT_PATTERNS),
        0.85 if primary in (RoleFamilyId.PRODUCT_MANAGEMENT, RoleFamilyId.PRODUCT_DELIVERY) else 0.0,
    )
    ops_required = max(
        _pattern_density(corpus, _OPS_PATTERNS),
        0.85 if primary in (RoleFamilyId.OPERATIONS, RoleFamilyId.ENTERPRISE_OPERATIONS) else 0.0,
    )
    arch_depth = max(
        _pattern_density(corpus, _ARCH_PATTERNS),
        0.75 if primary == RoleFamilyId.ENTERPRISE_ARCHITECTURE_DELIVERY else 0.0,
    )

    fake_resume = ParsedResume(raw_text=raw, job_titles=[title] if title else [], bullets=bullets)
    trans_result = TransformationInference().infer(fake_resume)
    ai_maturity = trans_result.ai_maturity

    heavy = _classify_job_heavy_flags(primary, {}, corpus, title)

    from career_intelligence_engine.intelligence.job_capability_vector import (
        extract_job_vector,
    )

    vector_result = extract_job_vector(
        corpus=corpus,
        title=title,
        bullets=bullets,
        job_hints={
            "governance_intensity": governance_intensity,
            "product_ownership_required": product_required,
            "operational_ownership_required": ops_required,
            "architecture_depth": arch_depth,
            "transformation_focus": trans_result.transformation_focus,
            "ai_maturity": ai_maturity,
            "primary_role_family": primary,
        },
    )

    heavy = _classify_job_heavy_flags(
        primary, vector_result.raw_scores, corpus, title
    )

    return JobProfile(
        title=title,
        raw_text=raw,
        role_family_candidates=candidates,
        primary_role_family=primary,
        required_seniority=required_seniority,
        leadership_scope=leadership_scope,
        architecture_depth=round(arch_depth, 3),
        product_ownership_required=round(product_required, 3),
        operational_ownership_required=round(ops_required, 3),
        ai_maturity_required=ai_maturity,
        transformation_type=transformation_type,
        governance_intensity=round(governance_intensity, 3),
        enterprise_scale=enterprise_scale,
        cloud_platform_indicators=cloud_indicators,
        capability_vector=vector_result.vector,
        capability_raw_scores=vector_result.raw_scores,
        is_product_heavy=heavy["is_product_heavy"],
        is_operations_heavy=heavy["is_operations_heavy"],
        is_architecture_heavy=heavy["is_architecture_heavy"],
        is_release_governance_heavy=heavy["is_release_governance_heavy"],
        is_ai_transformation=heavy["is_ai_transformation"],
        explanations={
            "role_family_scores": family_scores,
            "signals": {
                "title": title,
                "bullet_count": len(bullets),
                "sections": list(sections.keys()),
                "transformation_signals": trans_result.signals,
            },
            "vector_evidence": vector_result.evidence,
        },
    )
