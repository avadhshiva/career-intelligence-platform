"""Structured job description profile for deterministic matching."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from career_intelligence_engine.models.ontology import (
    AIMaturity,
    EnterpriseExposure,
    LeadershipLevel,
    RoleFamilyId,
    SeniorityLevel,
)


class JobProfile(BaseModel):
    """
    Deterministic job identity derived from a JD — parallel to CandidateProfile.
    All inference is rule-based and explainable via `explanations`.
    """

    title: str | None = None
    raw_text: str = ""
    role_family_candidates: list[RoleFamilyId] = Field(default_factory=list)
    primary_role_family: RoleFamilyId = RoleFamilyId.ENTERPRISE_DELIVERY
    required_seniority: SeniorityLevel = SeniorityLevel.UNKNOWN
    leadership_scope: LeadershipLevel = LeadershipLevel.UNKNOWN
    architecture_depth: float = Field(default=0.0, ge=0.0, le=1.0)
    product_ownership_required: float = Field(default=0.0, ge=0.0, le=1.0)
    operational_ownership_required: float = Field(default=0.0, ge=0.0, le=1.0)
    ai_maturity_required: AIMaturity = AIMaturity.NONE
    transformation_type: str = "none"
    governance_intensity: float = Field(default=0.0, ge=0.0, le=1.0)
    enterprise_scale: EnterpriseExposure = EnterpriseExposure.NONE
    cloud_platform_indicators: list[str] = Field(default_factory=list)
    capability_vector: dict[str, float] = Field(default_factory=dict)
    capability_raw_scores: dict[str, float] = Field(default_factory=dict)
    is_product_heavy: bool = False
    is_operations_heavy: bool = False
    is_architecture_heavy: bool = False
    is_release_governance_heavy: bool = False
    is_ai_transformation: bool = False
    explanations: dict[str, Any] = Field(default_factory=dict)
