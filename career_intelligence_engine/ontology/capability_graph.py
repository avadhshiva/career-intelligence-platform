"""Static enterprise capability clusters and deterministic skill normalization."""

from __future__ import annotations

import re

# Canonical capability cluster identifiers (keys used by role families and inference).
CAPABILITY_CLUSTERS: dict[str, list[str]] = {
    "enterprise_delivery": [
        "program management",
        "release management",
        "stakeholder management",
        "cross-functional",
        "governance",
        "execution",
        "delivery management",
        "benefits realization",
        "milestone management",
    ],
    "ai_transformation": [
        "generative ai",
        "genai",
        "llm",
        "large language model",
        "rag",
        "retrieval augmented generation",
        "responsible ai",
        "ai governance",
        "ai strategy",
        "mlops",
        "model governance",
    ],
    "enterprise_platforms": [
        "sap",
        "erp",
        "hybris",
        "azure",
        "cloud",
        "salesforce",
        "servicenow",
        "workday",
        "oracle",
        "dynamics",
    ],
    "program_portfolio_governance": [
        "portfolio management",
        "pmo",
        "program governance",
        "steering committee",
        "benefits tracking",
        "dependency management",
        "risk register",
        "stage gate",
    ],
    "technical_program_execution": [
        "technical program management",
        "engineering program",
        "sdlc",
        "ci/cd",
        "release train",
        "architecture alignment",
        "api",
        "platform engineering",
    ],
    "agile_at_scale": [
        "agile",
        "scrum",
        "safe",
        "pi planning",
        "sprint",
        "backlog refinement",
        "kanban",
    ],
    "stakeholder_executive_leadership": [
        "executive stakeholder",
        "c-suite",
        "board reporting",
        "executive sponsor",
        "steering facilitation",
        "influence without authority",
        "executive communication",
    ],
    "change_transformation": [
        "change management",
        "transformation",
        "operating model",
        "business transformation",
        "organizational change",
        "adoption",
        "change readiness",
    ],
    "cloud_infrastructure": [
        "cloud migration",
        "aws",
        "gcp",
        "kubernetes",
        "infrastructure as code",
        "terraform",
        "devops",
        "site reliability",
    ],
    "data_analytics_intelligence": [
        "data platform",
        "analytics",
        "business intelligence",
        "data governance",
        "data mesh",
        "etl",
        "warehouse",
    ],
    "product_strategy": [
        "product roadmap",
        "product strategy",
        "go-to-market",
        "product discovery",
        "prd",
        "user research",
        "product-market fit",
    ],
    "security_compliance": [
        "security",
        "compliance",
        "sox",
        "gdpr",
        "risk management",
        "audit",
        "controls",
    ],
    "financial_operations": [
        "fp&a",
        "budgeting",
        "financial modeling",
        "forecasting",
        "variance analysis",
        "cost management",
    ],
    "people_talent": [
        "talent acquisition",
        "hrbp",
        "people operations",
        "compensation",
        "employee relations",
        "performance management",
        "hris",
    ],
    "sales_gtm": [
        "enterprise sales",
        "pipeline",
        "quota",
        "account management",
        "solution selling",
        "crm",
    ],
    "software_engineering_craft": [
        "software engineering",
        "python",
        "java",
        "react",
        "typescript",
        "microservices",
        "system design",
        "code review",
    ],
    "release_quality_governance": [
        "release governance",
        "quality gate",
        "uat",
        "hypercare",
        "cutover",
        "release calendar",
        "defect triage",
    ],
    "enterprise_architecture": [
        "enterprise architecture",
        "solution architecture",
        "integration architecture",
        "reference architecture",
        "architecture review board",
        "togaf",
    ],
    "ai_governance_risk": [
        "model risk",
        "ai ethics",
        "bias testing",
        "model monitoring",
        "ai policy",
        "responsible ai framework",
    ],
    "operations_excellence": [
        "process improvement",
        "lean",
        "six sigma",
        "vendor management",
        "operating cadence",
        "okrs",
        "bizops",
    ],
}

# Maps aliases and abbreviations to canonical phrases used in clusters.
SKILL_SYNONYMS: dict[str, str] = {
    "tpm": "technical program management",
    "pmp": "program management",
    "pmi": "program management",
    "pm": "program management",
    "gen ai": "generative ai",
    "gen-ai": "generative ai",
    "gpt": "llm",
    "large language models": "large language model",
    "retrieval-augmented generation": "retrieval augmented generation",
    "rag pipeline": "rag",
    "ms azure": "azure",
    "microsoft azure": "azure",
    "amazon web services": "aws",
    "google cloud": "gcp",
    "k8s": "kubernetes",
    "iac": "infrastructure as code",
    "cicd": "ci/cd",
    "ci cd": "ci/cd",
    "scaled agile": "safe",
    "scaled agile framework": "safe",
    "exec stakeholder": "executive stakeholder",
    "xfn": "cross-functional",
    "cross functional": "cross-functional",
    "stakeholder mgmt": "stakeholder management",
    "prog mgmt": "program management",
    "rel mgmt": "release management",
    "ea": "enterprise architecture",
    "togaf certified": "togaf",
    "ai/ml": "ai strategy",
    "machine learning": "ai strategy",
    "ml ops": "mlops",
    "prompt eng": "generative ai",
    "prompt engineering": "generative ai",
    "openai": "llm",
    "azure openai": "llm",
    "bedrock": "llm",
    "servicenow itsm": "servicenow",
    "sfdc": "salesforce",
    "hr bp": "hrbp",
    "people ops": "people operations",
    "gtm": "go-to-market",
    "finops": "cost management",
    "dev sec ops": "devops",
    "sre": "site reliability",
}


def _normalize_key(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation edges."""
    cleaned = re.sub(r"[^\w\s/&+-]", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


_SYNONYM_LOOKUP: dict[str, str] = {
    _normalize_key(alias): canonical for alias, canonical in SKILL_SYNONYMS.items()
}

_CLUSTER_TERM_INDEX: dict[str, str] = {}
for _cluster_id, _terms in CAPABILITY_CLUSTERS.items():
    for _term in _terms:
        _CLUSTER_TERM_INDEX[_normalize_key(_term)] = _cluster_id


def normalize_skill(skill: str) -> str:
    """Map a raw skill phrase to its canonical form using static synonyms."""
    key = _normalize_key(skill)
    if key in _SYNONYM_LOOKUP:
        return _SYNONYM_LOOKUP[key]
    return key


def normalize_skills(skills: list[str]) -> list[str]:
    """Normalize and deduplicate skill phrases while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for skill in skills:
        canonical = normalize_skill(skill)
        if canonical and canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return result


def cluster_for_term(term: str) -> str | None:
    """Return capability cluster id if term matches a cluster phrase."""
    key = _normalize_key(normalize_skill(term))
    return _CLUSTER_TERM_INDEX.get(key)


def all_cluster_ids() -> list[str]:
    return list(CAPABILITY_CLUSTERS.keys())
