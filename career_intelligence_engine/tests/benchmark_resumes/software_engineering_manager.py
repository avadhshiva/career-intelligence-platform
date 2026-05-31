"""Benchmark: software engineering manager."""

from __future__ import annotations

from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.tests.benchmark_resumes.schema import (
    BenchmarkResumeFixture,
    CapabilityTraitRange,
)

RESUME_TEXT = """
Riley Park | riley.park@email.com

EXPERIENCE
Engineering Manager | Tech Co | 2017 – Present
• Software engineering team lead with 12 developers and hiring ownership
• Code review, pull request standards, and full stack delivery accountability
• Owned production systems, kubernetes platform, and CI/CD pipelines
• Backend development in Python and Java with architecture review participation

Senior Software Engineer | Dev Shop | 2012 – 2017
• Unit testing, software engineer delivery, and system design

SKILLS
Software engineering, Python, Java, kubernetes, CI/CD, code review, pull request
"""

FIXTURE = BenchmarkResumeFixture(
    fixture_id="software_engineering_manager",
    resume_text=RESUME_TEXT,
    expected_primary=RoleFamilyId.SOFTWARE_ENGINEERING,
    expected_adjacent=(
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
        RoleFamilyId.PLATFORM_MODERNIZATION,
    ),
    forbidden_families=(
        RoleFamilyId.PROGRAM_LEADERSHIP,
        RoleFamilyId.AI_TRANSFORMATION,
        RoleFamilyId.HR,
    ),
    excluded_families=(),
    capability_traits=(
        CapabilityTraitRange("engineering_depth", 0.15, 0.80),
        CapabilityTraitRange("technical_execution", 0.10, 0.65),
        CapabilityTraitRange("portfolio_management", 0.0, 0.25),
        CapabilityTraitRange("enterprise_governance", 0.0, 0.30),
    ),
    description="Hands-on engineering manager; program leadership must not be primary.",
)
