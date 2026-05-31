"""Benchmark: IT / service operations manager."""

from __future__ import annotations

from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.tests.benchmark_resumes.schema import (
    BenchmarkResumeFixture,
    CapabilityTraitRange,
)

RESUME_TEXT = """
Morgan Lee | morgan.lee@email.com

EXPERIENCE
Operations Manager | Ops Corp | 2016 – Present
• Run operations for production systems with SLA management and incident management
• Service operations, NOC coordination, and operational continuity programs
• IT operations support model and production support for hosted services

Operations Analyst | Host Co | 2010 – 2016
• IT operations, incident management, and service operations

SKILLS
IT operations, SLA, incident management, service operations, production support, NOC, run operations
"""

FIXTURE = BenchmarkResumeFixture(
    fixture_id="operations_manager",
    resume_text=RESUME_TEXT,
    expected_primary=RoleFamilyId.OPERATIONS,
    expected_adjacent=(
        RoleFamilyId.ENTERPRISE_OPERATIONS,
        RoleFamilyId.ENTERPRISE_DELIVERY,
    ),
    forbidden_families=(
        RoleFamilyId.AI_TRANSFORMATION,
        RoleFamilyId.PROGRAM_LEADERSHIP,
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
    ),
    excluded_families=(),
    capability_traits=(
        CapabilityTraitRange("operational_management", 0.15, 0.65),
        CapabilityTraitRange("delivery_execution", 0.05, 0.40),
        CapabilityTraitRange("ai_strategy", 0.0, 0.25),
        CapabilityTraitRange("portfolio_management", 0.0, 0.25),
    ),
    description="Run-state operations leader; program leadership must not be primary.",
)
