"""Benchmark: release governance / release train lead."""

from __future__ import annotations

from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.tests.benchmark_resumes.schema import (
    BenchmarkResumeFixture,
    CapabilityTraitRange,
)

RESUME_TEXT = """
Pat Olsen | pat.olsen@email.com

EXPERIENCE
Release Governance Lead | ShipCo | 2016 – Present
• Owned release calendar, cutover planning, UAT coordination, and hypercare
• Release train engineer for SAFe ART with quality gates and release governance
• SDLC and CI/CD pipeline governance across platform teams
• Dependency management and release readiness reviews

Release Manager | BuildSys | 2011 – 2016
• Release management, cutover, production deployment governance

SKILLS
Release management, release train, CI/CD, SDLC, SAFE, quality gate, agile
"""

FIXTURE = BenchmarkResumeFixture(
    fixture_id="release_governance_lead",
    resume_text=RESUME_TEXT,
    expected_primary=RoleFamilyId.RELEASE_GOVERNANCE,
    expected_adjacent=(
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
        RoleFamilyId.ENTERPRISE_DELIVERY,
    ),
    forbidden_families=(
        RoleFamilyId.PRODUCT_MANAGEMENT,
        RoleFamilyId.AI_GOVERNANCE,
        RoleFamilyId.HR,
    ),
    excluded_families=(),
    capability_traits=(
        CapabilityTraitRange("release_governance", 0.12, 0.60),
        CapabilityTraitRange("technical_execution", 0.08, 0.65),
        CapabilityTraitRange("delivery_execution", 0.05, 0.55),
        CapabilityTraitRange("product_thinking", 0.0, 0.18),
    ),
    description="Release-focused leader; product and AI governance must not dominate.",
)
