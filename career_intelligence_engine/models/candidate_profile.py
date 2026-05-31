"""Candidate career identity profile."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from career_intelligence_engine.models.evaluation import ConfidenceResult
from career_intelligence_engine.models.ontology import (
    AIMaturity,
    CompanyArchetypeId,
    EnterpriseExposure,
    LeadershipLevel,
    RoleFamilyId,
    SeniorityLevel,
)


class CandidateProfile(BaseModel):
    """
    Structured professional identity — not a keyword bag.
    All inference is deterministic and explainable via `explanations`.
    """

    full_name: str | None = None
    years_experience: float | None = None
    current_seniority: SeniorityLevel = SeniorityLevel.UNKNOWN
    leadership_level: LeadershipLevel = LeadershipLevel.UNKNOWN
    primary_career_track: RoleFamilyId = RoleFamilyId.OPERATIONS
    adjacent_role_families: list[RoleFamilyId] = Field(default_factory=list)
    primary_domains: list[str] = Field(default_factory=list)
    secondary_domains: list[str] = Field(default_factory=list)
    enterprise_experience: EnterpriseExposure = EnterpriseExposure.NONE
    delivery_orientation: float = Field(default=0.0, ge=0.0, le=1.0)
    transformation_focus: float = Field(default=0.0, ge=0.0, le=1.0)
    ai_maturity: AIMaturity = AIMaturity.NONE
    likely_target_company_archetypes: list[CompanyArchetypeId] = Field(
        default_factory=list
    )
    inferred_locations: list[str] = Field(default_factory=list)
    top_skills: list[str] = Field(default_factory=list)
    governance_experience: float = Field(default=0.0, ge=0.0, le=1.0)
    stakeholder_complexity: float = Field(default=0.0, ge=0.0, le=1.0)
    execution_orientation: float = Field(default=0.0, ge=0.0, le=1.0)
    strategic_orientation: float = Field(default=0.0, ge=0.0, le=1.0)
    role_family_scores: dict[str, float] = Field(default_factory=dict)
    capability_vector: dict[str, float] = Field(default_factory=dict)
    capability_raw_scores: dict[str, float] = Field(default_factory=dict)
    confidence_result: ConfidenceResult | None = None
    explanations: dict[str, Any] = Field(default_factory=dict)
