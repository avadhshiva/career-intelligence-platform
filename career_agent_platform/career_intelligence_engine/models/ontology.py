"""Core ontology types for career identity and matching."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class RoleFamilyId(str, Enum):
    PROGRAM_LEADERSHIP = "program_leadership"
    TECHNICAL_PROGRAM_MANAGEMENT = "technical_program_management"
    AI_TRANSFORMATION = "ai_transformation"
    AI_PROGRAM_MANAGEMENT = "ai_program_management"
    ENTERPRISE_DELIVERY = "enterprise_delivery"
    TRANSFORMATION_OFFICE = "transformation_office"
    ENTERPRISE_ARCHITECTURE_DELIVERY = "enterprise_architecture_delivery"
    PLATFORM_MODERNIZATION = "platform_modernization"
    RELEASE_GOVERNANCE = "release_governance"
    DIGITAL_TRANSFORMATION = "digital_transformation"
    PRODUCT_DELIVERY = "product_delivery"
    ENTERPRISE_OPERATIONS = "enterprise_operations"
    AI_GOVERNANCE = "ai_governance"
    CLOUD_TRANSFORMATION = "cloud_transformation"
    PRODUCT_MANAGEMENT = "product_management"
    HR = "hr"
    SOFTWARE_ENGINEERING = "software_engineering"
    SALES = "sales"
    FINANCE = "finance"
    OPERATIONS = "operations"


class CompanyArchetypeId(str, Enum):
    GLOBAL_ENTERPRISE = "global_enterprise"
    MID_MARKET_ENTERPRISE = "mid_market_enterprise"
    TECH_SCALE_UP = "tech_scale_up"
    CONSULTING_SERVICES = "consulting_services"
    REGULATED_INDUSTRY = "regulated_industry"
    PUBLIC_SECTOR = "public_sector"
    STARTUP_VENTURE = "startup_venture"
    PRODUCT_LED_SAAS = "product_led_saas"


class SeniorityLevel(str, Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"
    DIRECTOR = "director"
    VP = "vp"
    C_LEVEL = "c_level"
    UNKNOWN = "unknown"


class LeadershipLevel(str, Enum):
    INDIVIDUAL_CONTRIBUTOR = "individual_contributor"
    TEAM_LEAD = "team_lead"
    PEOPLE_MANAGER = "people_manager"
    ORG_LEADER = "org_leader"
    EXECUTIVE = "executive"
    UNKNOWN = "unknown"


class EnterpriseExposure(str, Enum):
    NONE = "none"
    LIMITED = "limited"
    MODERATE = "moderate"
    STRONG = "strong"
    DEEP = "deep"


class AIMaturity(str, Enum):
    NONE = "none"
    AWARENESS = "awareness"
    PILOT = "pilot"
    PRACTITIONER = "practitioner"
    TRANSFORMATION_LEAD = "transformation_lead"
    ENTERPRISE_AI_OWNER = "enterprise_ai_owner"
    SCALING = "practitioner"  # legacy alias


class RoleFamilyDefinition(BaseModel):
    """Ontology entry for a role family with semantic scoring metadata."""

    id: RoleFamilyId
    display_name: str
    canonical_titles: list[str]
    adjacent_families: list[RoleFamilyId]
    excluded_families: list[RoleFamilyId]
    seniority_patterns: list[str]
    title_signals: list[str] = Field(default_factory=list)
    experience_signals: list[str] = Field(default_factory=list)
    skill_signals: list[str] = Field(default_factory=list)
    primary_capabilities: list[str] = Field(default_factory=list)
    secondary_capabilities: list[str] = Field(default_factory=list)
    leadership_intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    transformation_intensity: float = Field(default=0.0, ge=0.0, le=1.0)
    enterprise_depth: float = Field(default=0.5, ge=0.0, le=1.0)
    # Phase 2 semantic ontology fields
    canonical_name: str = ""
    positive_signals: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    executive_signals: list[str] = Field(default_factory=list)
    far_families: list[RoleFamilyId] = Field(default_factory=list)
    archetype_keywords: list[str] = Field(default_factory=list)
    governance_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    delivery_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    strategy_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    execution_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    transformation_weight: float = Field(default=0.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _populate_semantic_defaults(self) -> RoleFamilyDefinition:
        if not self.canonical_name:
            self.canonical_name = self.display_name
        if not self.positive_signals:
            self.positive_signals = list(
                dict.fromkeys(
                    self.title_signals + self.experience_signals + self.skill_signals
                )
            )
        return self


class CompanyArchetypeDefinition(BaseModel):
    """Company environment archetype (no specific company names)."""

    id: CompanyArchetypeId
    display_name: str
    description: str
    exposure_signals: list[str] = Field(default_factory=list)
    scale_signals: list[str] = Field(default_factory=list)


class ParsedResume(BaseModel):
    """Structured output from resume parsing."""

    raw_text: str
    full_name: str | None = None
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    job_titles: list[str] = Field(default_factory=list)
    employers: list[str] = Field(default_factory=list)
    date_ranges: list[str] = Field(default_factory=list)
    years_experience: float | None = None
    sections: dict[str, str] = Field(default_factory=dict)
    bullets: list[str] = Field(default_factory=list)


class CareerDistanceInput(BaseModel):
    """Inputs for career-distance scoring between two identity vectors."""

    source_role_family: RoleFamilyId
    target_role_family: RoleFamilyId
    source_seniority: SeniorityLevel
    target_seniority: SeniorityLevel
    source_leadership: LeadershipLevel
    target_leadership: LeadershipLevel
    source_domains: list[str] = Field(default_factory=list)
    target_domains: list[str] = Field(default_factory=list)
    source_enterprise: EnterpriseExposure
    target_enterprise: EnterpriseExposure
    source_transformation: float = 0.0
    target_transformation: float = 0.0


class CareerDistanceResult(BaseModel):
    """Explainable career proximity score (0 = identical track, higher = farther)."""

    distance: float
    proximity: float
    components: dict[str, float]
    explanation: list[str]
    # Vector-proximity fields (optional for legacy graph-based scoring)
    semantic_distance: float | None = None
    dominant_dimensions: list[str] = Field(default_factory=list)
    weak_dimensions: list[str] = Field(default_factory=list)
    missing_dimensions: list[str] = Field(default_factory=list)
    vector_explanation: str | None = None
