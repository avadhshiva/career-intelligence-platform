"""Deterministic resume variant library."""

from __future__ import annotations

from dataclasses import dataclass, field

from career_intelligence_engine.models.ontology import RoleFamilyId


@dataclass(frozen=True)
class ResumeVariant:
    variant_id: str
    label: str
    primary_focus: str
    strengths: tuple[str, ...]
    suitable_role_families: tuple[str, ...]
    unsuitable_role_families: tuple[str, ...] = field(default_factory=tuple)


RESUME_VARIANTS: dict[str, ResumeVariant] = {
    "ai_transformation": ResumeVariant(
        variant_id="ai_transformation",
        label="Senior Manager – AI Transformation & Enterprise Operating Model",
        primary_focus="AI transformation",
        strengths=(
            "Enterprise AI strategy and operating-model redesign",
            "Transformation office coordination",
            "Executive sponsorship and adoption metrics",
        ),
        suitable_role_families=(
            RoleFamilyId.AI_TRANSFORMATION.value,
            RoleFamilyId.TRANSFORMATION_OFFICE.value,
            RoleFamilyId.DIGITAL_TRANSFORMATION.value,
        ),
        unsuitable_role_families=(RoleFamilyId.RELEASE_GOVERNANCE.value, RoleFamilyId.OPERATIONS.value),
    ),
    "ai_enablement": ResumeVariant(
        variant_id="ai_enablement",
        label="Senior Manager – AI Enablement & Enterprise Automation",
        primary_focus="AI enablement",
        strengths=(
            "AI workflow modernization evidence",
            "Cross-functional AI adoption programs",
            "Platform automation and MLOps coordination",
        ),
        suitable_role_families=(
            RoleFamilyId.AI_PROGRAM_MANAGEMENT.value,
            RoleFamilyId.AI_GOVERNANCE.value,
            RoleFamilyId.PLATFORM_MODERNIZATION.value,
        ),
        unsuitable_role_families=(RoleFamilyId.PRODUCT_MANAGEMENT.value,),
    ),
    "tpm": ResumeVariant(
        variant_id="tpm",
        label="Senior Technical Program Manager – Enterprise Platform Delivery",
        primary_focus="technical program management",
        strengths=(
            "Cross-functional technical delivery",
            "Architecture alignment and dependency management",
            "Engineering stakeholder coordination",
        ),
        suitable_role_families=(RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT.value,),
        unsuitable_role_families=(RoleFamilyId.PRODUCT_MANAGEMENT.value, RoleFamilyId.SALES.value),
    ),
    "release_governance": ResumeVariant(
        variant_id="release_governance",
        label="Delivery Lead – Release Governance & Agile-at-Scale",
        primary_focus="release governance",
        strengths=(
            "Release train and PI planning leadership",
            "SDLC governance and deployment quality",
            "Compliance-aware release coordination",
        ),
        suitable_role_families=(RoleFamilyId.RELEASE_GOVERNANCE.value,),
        unsuitable_role_families=(RoleFamilyId.AI_TRANSFORMATION.value, RoleFamilyId.PRODUCT_MANAGEMENT.value),
    ),
    "enterprise_delivery": ResumeVariant(
        variant_id="enterprise_delivery",
        label="Senior Manager – Enterprise Delivery & Program Governance",
        primary_focus="enterprise delivery",
        strengths=(
            "Large-scale program delivery",
            "Matrix stakeholder leadership",
            "Consulting-style PMO execution",
        ),
        suitable_role_families=(
            RoleFamilyId.ENTERPRISE_DELIVERY.value,
            RoleFamilyId.PROGRAM_LEADERSHIP.value,
        ),
        unsuitable_role_families=(RoleFamilyId.SOFTWARE_ENGINEERING.value,),
    ),
    "program_leadership": ResumeVariant(
        variant_id="program_leadership",
        label="Program Director – Portfolio Governance & Executive Delivery",
        primary_focus="program leadership",
        strengths=(
            "Portfolio governance and benefits realization",
            "Executive steering and cross-functional alignment",
            "Multi-program orchestration",
        ),
        suitable_role_families=(RoleFamilyId.PROGRAM_LEADERSHIP.value,),
        unsuitable_role_families=(RoleFamilyId.SOFTWARE_ENGINEERING.value,),
    ),
}

DEFAULT_VARIANT_ORDER: tuple[str, ...] = (
    "enterprise_delivery",
    "tpm",
    "release_governance",
    "ai_enablement",
    "ai_transformation",
    "program_leadership",
)
