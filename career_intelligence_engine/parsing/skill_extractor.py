"""Deterministic skill and domain signal extraction from resume text."""

from __future__ import annotations

import re
from collections import Counter

# Curated skill/domain lexicon — expandable without LLM
_SKILL_LEXICON: dict[str, list[str]] = {
    "program_management": [
        "program management",
        "portfolio management",
        "pmo",
        "pmp",
        "pmi",
        "benefits realization",
        "stakeholder management",
    ],
    "technical_delivery": [
        "technical program",
        "sdlc",
        "release management",
        "dependency management",
        "architecture",
        "api",
        "ci/cd",
        "devops",
    ],
    "ai_ml": [
        "machine learning",
        "artificial intelligence",
        "genai",
        "generative ai",
        "llm",
        "prompt engineering",
        "mlops",
        "responsible ai",
        "rag",
    ],
    "enterprise_systems": [
        "sap",
        "salesforce",
        "servicenow",
        "workday",
        "erp",
        "crm",
        "oracle",
    ],
    "cloud": ["aws", "azure", "gcp", "kubernetes", "terraform", "cloud"],
    "data": ["sql", "python", "tableau", "power bi", "data analytics", "etl"],
    "product": ["product management", "roadmap", "prd", "user research", "agile"],
    "governance": [
        "governance",
        "risk",
        "compliance",
        "sox",
        "gdpr",
        "hipaa",
        "audit",
        "controls",
    ],
    "leadership": [
        "executive",
        "c-suite",
        "board",
        "cross-functional",
        "org design",
        "change management",
    ],
    "finance_domain": ["fp&a", "financial modeling", "budgeting", "forecasting"],
    "hr_domain": ["hrbp", "talent acquisition", "compensation", "employee relations"],
    "engineering": [
        "software engineer",
        "react",
        "typescript",
        "java",
        "microservices",
        "system design",
    ],
    "sales_domain": ["quota", "pipeline", "account executive", "enterprise sales"],
}

_DOMAIN_LABELS: dict[str, str] = {
    "program_management": "Program & Portfolio Management",
    "technical_delivery": "Technology Delivery",
    "ai_ml": "AI & Machine Learning",
    "enterprise_systems": "Enterprise Platforms",
    "cloud": "Cloud Infrastructure",
    "data": "Data & Analytics",
    "product": "Product",
    "governance": "Governance & Compliance",
    "leadership": "Organizational Leadership",
    "finance_domain": "Finance",
    "hr_domain": "Human Resources",
    "engineering": "Software Engineering",
    "sales_domain": "Sales & GTM",
}


class SkillExtractor:
    """Match resume text against a curated lexicon; rank by frequency and position."""

    def extract(self, text: str, bullets: list[str] | None = None) -> dict[str, list[str]]:
        normalized = text.lower()
        bullet_text = "\n".join(bullets or []).lower()
        combined = f"{normalized}\n{bullet_text}"

        skill_hits: Counter[str] = Counter()
        domain_scores: Counter[str] = Counter()

        for domain_key, phrases in _SKILL_LEXICON.items():
            for phrase in phrases:
                pattern = re.compile(re.escape(phrase.lower()))
                count = len(pattern.findall(combined))
                if count:
                    skill_hits[phrase] += count
                    domain_scores[domain_key] += count

        top_skills = [s for s, _ in skill_hits.most_common(25)]
        ranked_domains = domain_scores.most_common()
        primary = [
            _DOMAIN_LABELS[k]
            for k, score in ranked_domains[:3]
            if score > 0 and k in _DOMAIN_LABELS
        ]
        secondary = [
            _DOMAIN_LABELS[k]
            for k, score in ranked_domains[3:6]
            if score > 0 and k in _DOMAIN_LABELS
        ]

        return {
            "top_skills": top_skills,
            "primary_domains": primary,
            "secondary_domains": secondary,
            "domain_scores": {k: float(v) for k, v in domain_scores.items()},
        }
