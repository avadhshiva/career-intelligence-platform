"""Capability vector ontology — mathematically distinct role-family profiles."""

from __future__ import annotations

import math
from typing import Mapping

from career_intelligence_engine.models.ontology import RoleFamilyId

# Ordered capability dimensions (fixed basis for all vectors)
CAPABILITY_DIMENSIONS: tuple[str, ...] = (
    "enterprise_governance",
    "technical_execution",
    "transformation_strategy",
    "ai_strategy",
    "delivery_execution",
    "stakeholder_complexity",
    "organizational_leadership",
    "operational_management",
    "product_thinking",
    "engineering_depth",
    "release_governance",
    "architecture_coordination",
    "portfolio_management",
    "executive_communication",
    "change_management",
)

DIMENSION_LABELS: dict[str, str] = {
    "enterprise_governance": "Enterprise Governance",
    "technical_execution": "Technical Execution",
    "transformation_strategy": "Transformation Strategy",
    "ai_strategy": "AI Strategy",
    "delivery_execution": "Delivery Execution",
    "stakeholder_complexity": "Stakeholder Complexity",
    "organizational_leadership": "Organizational Leadership",
    "operational_management": "Operational Management",
    "product_thinking": "Product Thinking",
    "engineering_depth": "Engineering Depth",
    "release_governance": "Release Governance",
    "architecture_coordination": "Architecture Coordination",
    "portfolio_management": "Portfolio Management",
    "executive_communication": "Executive Communication",
    "change_management": "Change Management",
}

# Sparse role-family vectors — only non-zero weights stored; normalized on read.
_ROLE_FAMILY_VECTORS_RAW: dict[RoleFamilyId, dict[str, float]] = {
    RoleFamilyId.PROGRAM_LEADERSHIP: {
        "portfolio_management": 0.9,
        "enterprise_governance": 0.85,
        "stakeholder_complexity": 0.8,
        "executive_communication": 0.75,
        "organizational_leadership": 0.7,
        "delivery_execution": 0.55,
        "transformation_strategy": 0.45,
        "change_management": 0.4,
    },
    RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT: {
        "technical_execution": 0.9,
        "release_governance": 0.8,
        "architecture_coordination": 0.7,
        "delivery_execution": 0.65,
        "stakeholder_complexity": 0.5,
        "executive_communication": 0.4,
        "engineering_depth": 0.35,
        "ai_strategy": 0.2,
    },
    RoleFamilyId.AI_PROGRAM_MANAGEMENT: {
        "ai_strategy": 0.85,
        "technical_execution": 0.75,
        "release_governance": 0.7,
        "portfolio_management": 0.65,
        "delivery_execution": 0.6,
        "stakeholder_complexity": 0.55,
        "architecture_coordination": 0.5,
        "executive_communication": 0.45,
    },
    RoleFamilyId.AI_TRANSFORMATION: {
        "ai_strategy": 0.9,
        "transformation_strategy": 0.9,
        "organizational_leadership": 0.8,
        "executive_communication": 0.8,
        "change_management": 0.7,
        "enterprise_governance": 0.55,
        "technical_execution": 0.3,
    },
    RoleFamilyId.ENTERPRISE_DELIVERY: {
        "delivery_execution": 0.9,
        "stakeholder_complexity": 0.75,
        "enterprise_governance": 0.6,
        "operational_management": 0.45,
        "change_management": 0.4,
        "portfolio_management": 0.35,
    },
    RoleFamilyId.TRANSFORMATION_OFFICE: {
        "transformation_strategy": 0.95,
        "change_management": 0.9,
        "enterprise_governance": 0.85,
        "portfolio_management": 0.8,
        "organizational_leadership": 0.75,
        "executive_communication": 0.7,
        "stakeholder_complexity": 0.6,
    },
    RoleFamilyId.ENTERPRISE_ARCHITECTURE_DELIVERY: {
        "architecture_coordination": 0.9,
        "technical_execution": 0.75,
        "enterprise_governance": 0.7,
        "delivery_execution": 0.65,
        "engineering_depth": 0.6,
        "stakeholder_complexity": 0.5,
    },
    RoleFamilyId.PLATFORM_MODERNIZATION: {
        "technical_execution": 0.85,
        "architecture_coordination": 0.8,
        "engineering_depth": 0.75,
        "transformation_strategy": 0.65,
        "delivery_execution": 0.6,
        "release_governance": 0.55,
    },
    RoleFamilyId.RELEASE_GOVERNANCE: {
        "release_governance": 0.95,
        "technical_execution": 0.75,
        "architecture_coordination": 0.6,
        "delivery_execution": 0.55,
        "enterprise_governance": 0.45,
        "stakeholder_complexity": 0.4,
    },
    RoleFamilyId.DIGITAL_TRANSFORMATION: {
        "transformation_strategy": 0.9,
        "change_management": 0.85,
        "delivery_execution": 0.7,
        "product_thinking": 0.55,
        "executive_communication": 0.6,
        "stakeholder_complexity": 0.55,
    },
    RoleFamilyId.PRODUCT_DELIVERY: {
        "product_thinking": 0.8,
        "delivery_execution": 0.85,
        "stakeholder_complexity": 0.6,
        "release_governance": 0.55,
        "technical_execution": 0.45,
    },
    RoleFamilyId.ENTERPRISE_OPERATIONS: {
        "operational_management": 0.9,
        "delivery_execution": 0.65,
        "enterprise_governance": 0.55,
        "stakeholder_complexity": 0.4,
        "change_management": 0.35,
    },
    RoleFamilyId.AI_GOVERNANCE: {
        "ai_strategy": 0.85,
        "enterprise_governance": 0.85,
        "release_governance": 0.6,
        "executive_communication": 0.55,
        "stakeholder_complexity": 0.5,
        "transformation_strategy": 0.45,
    },
    RoleFamilyId.CLOUD_TRANSFORMATION: {
        "transformation_strategy": 0.85,
        "technical_execution": 0.8,
        "architecture_coordination": 0.75,
        "delivery_execution": 0.65,
        "change_management": 0.6,
        "engineering_depth": 0.55,
    },
    RoleFamilyId.PRODUCT_MANAGEMENT: {
        "product_thinking": 0.95,
        "stakeholder_complexity": 0.7,
        "delivery_execution": 0.55,
        "executive_communication": 0.5,
        "transformation_strategy": 0.35,
    },
    RoleFamilyId.HR: {
        "organizational_leadership": 0.85,
        "change_management": 0.75,
        "stakeholder_complexity": 0.6,
        "operational_management": 0.5,
    },
    RoleFamilyId.SOFTWARE_ENGINEERING: {
        "engineering_depth": 0.95,
        "technical_execution": 0.9,
        "architecture_coordination": 0.6,
        "release_governance": 0.45,
    },
    RoleFamilyId.SALES: {
        "stakeholder_complexity": 0.75,
        "executive_communication": 0.7,
        "product_thinking": 0.45,
    },
    RoleFamilyId.FINANCE: {
        "enterprise_governance": 0.75,
        "operational_management": 0.65,
        "portfolio_management": 0.6,
        "stakeholder_complexity": 0.45,
    },
    RoleFamilyId.OPERATIONS: {
        "operational_management": 0.95,
        "delivery_execution": 0.6,
        "stakeholder_complexity": 0.35,
        "change_management": 0.3,
    },
}

# Pre-normalized vectors for all role families
ROLE_FAMILY_VECTORS: dict[RoleFamilyId, dict[str, float]] = {}


def normalize_vector(raw: Mapping[str, float]) -> dict[str, float]:
    """L2-normalize a sparse vector over the full dimension basis."""
    full = {d: float(raw.get(d, 0.0)) for d in CAPABILITY_DIMENSIONS}
    norm = math.sqrt(sum(v * v for v in full.values()))
    if norm <= 0.0:
        return {d: 0.0 for d in CAPABILITY_DIMENSIONS}
    return {d: round(v / norm, 4) for d, v in full.items()}


def _init_vectors() -> None:
    for family_id, raw in _ROLE_FAMILY_VECTORS_RAW.items():
        ROLE_FAMILY_VECTORS[family_id] = normalize_vector(raw)


_init_vectors()


def get_role_family_vector(family_id: RoleFamilyId) -> dict[str, float]:
    """Return the normalized capability vector for a role family."""
    return dict(ROLE_FAMILY_VECTORS[family_id])


def empty_vector() -> dict[str, float]:
    return {d: 0.0 for d in CAPABILITY_DIMENSIONS}


def cosine_similarity(
    a: Mapping[str, float],
    b: Mapping[str, float],
) -> float:
    """Cosine similarity between two capability vectors (0–1 for non-negative vectors)."""
    dot = sum(float(a.get(d, 0.0)) * float(b.get(d, 0.0)) for d in CAPABILITY_DIMENSIONS)
    norm_a = math.sqrt(sum(float(a.get(d, 0.0)) ** 2 for d in CAPABILITY_DIMENSIONS))
    norm_b = math.sqrt(sum(float(b.get(d, 0.0)) ** 2 for d in CAPABILITY_DIMENSIONS))
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return round(min(1.0, dot / (norm_a * norm_b)), 4)


def dimension_contributions(
    candidate: Mapping[str, float],
    role_family: Mapping[str, float],
    *,
    top_n: int = 4,
) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    """
    Identify dominant and weak dimensions by per-dimension product contribution.

    Returns (dominant, weak) as lists of (dimension_id, contribution) sorted by magnitude.
    """
    products: list[tuple[str, float]] = []
    for dim in CAPABILITY_DIMENSIONS:
        c_val = float(candidate.get(dim, 0.0))
        r_val = float(role_family.get(dim, 0.0))
        if r_val >= 0.15:
            products.append((dim, c_val * r_val))

    products.sort(key=lambda x: -x[1])
    dominant = products[:top_n]

    weak = [
        (dim, contrib)
        for dim, contrib in products
        if contrib < 0.05 and float(role_family.get(dim, 0.0)) >= 0.25
    ]
    weak.sort(key=lambda x: x[1])
    return dominant, weak[:top_n]


def label_dimension(dimension_id: str) -> str:
    return DIMENSION_LABELS.get(dimension_id, dimension_id.replace("_", " ").title())
