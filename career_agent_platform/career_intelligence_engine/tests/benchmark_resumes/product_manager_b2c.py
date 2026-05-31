"""Benchmark: B2C product manager."""

from __future__ import annotations

from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.tests.benchmark_resumes.schema import (
    BenchmarkResumeFixture,
    CapabilityTraitRange,
)

RESUME_TEXT = """
Casey Nguyen | casey.nguyen@email.com

EXPERIENCE
Senior Product Manager | Consumer Apps Inc | 2018 – Present
• Owned B2C product roadmap, PRD, and user research for mobile consumer app
• Led customer discovery, A/B testing, and go-to-market for consumer features
• Product-market fit experiments and product strategy with engineering partners
• Feature prioritization and product lifecycle for millions of users

Product Manager | App Co | 2014 – 2018
• Product owner for consumer product delivery and launch planning

SKILLS
Product roadmap, PRD, user research, go-to-market, A/B testing, Figma, product strategy
"""

FIXTURE = BenchmarkResumeFixture(
    fixture_id="product_manager_b2c",
    resume_text=RESUME_TEXT,
    expected_primary=RoleFamilyId.PRODUCT_MANAGEMENT,
    expected_adjacent=(
        RoleFamilyId.PRODUCT_DELIVERY,
    ),
    forbidden_families=(
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
        RoleFamilyId.RELEASE_GOVERNANCE,
        RoleFamilyId.HR,
    ),
    excluded_families=(),
    capability_traits=(
        CapabilityTraitRange("product_thinking", 0.15, 0.95),
        CapabilityTraitRange("delivery_execution", 0.05, 0.40),
        CapabilityTraitRange("technical_execution", 0.0, 0.30),
        CapabilityTraitRange("release_governance", 0.0, 0.25),
    ),
    description="B2C PM with roadmap/PRD signals; TPM/release tracks should not lead.",
)
