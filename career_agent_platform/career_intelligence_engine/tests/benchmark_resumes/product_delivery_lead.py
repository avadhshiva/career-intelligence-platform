"""Benchmark: product delivery lead."""

from __future__ import annotations

from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.tests.benchmark_resumes.schema import (
    BenchmarkResumeFixture,
    CapabilityTraitRange,
)

RESUME_TEXT = """
Blake Torres | blake.torres@email.com

EXPERIENCE
Product Operations Manager | LaunchCo | 2018 – Present
• Owned product delivery operations and product launch governance for SaaS platform
• Product lifecycle management, product operations, and product launch cadence
• Product delivery lead for product launch and product operations across the portfolio
• Product lifecycle ownership with backlog ownership for product delivery outcomes

Product Delivery Lead | SaaS Co | 2013 – 2018
• Product delivery, product launch, product lifecycle, and product operations

SKILLS
Product delivery, product launch, product lifecycle, product operations, product delivery lead, backlog ownership
"""

FIXTURE = BenchmarkResumeFixture(
    fixture_id="product_delivery_lead",
    resume_text=RESUME_TEXT,
    expected_primary=RoleFamilyId.PRODUCT_DELIVERY,
    expected_adjacent=(
        RoleFamilyId.PRODUCT_MANAGEMENT,
    ),
    forbidden_families=(
        RoleFamilyId.RELEASE_GOVERNANCE,
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
    ),
    excluded_families=(),
    capability_traits=(
        CapabilityTraitRange("product_thinking", 0.05, 0.70),
        CapabilityTraitRange("delivery_execution", 0.10, 0.70),
        CapabilityTraitRange("release_governance", 0.0, 0.35),
        CapabilityTraitRange("operational_management", 0.0, 0.25),
    ),
    description="Product delivery director; product delivery must beat product management.",
)
