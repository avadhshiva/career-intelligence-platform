"""Benchmark: AI transformation director."""

from __future__ import annotations

from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.tests.benchmark_resumes.schema import (
    BenchmarkResumeFixture,
    CapabilityTraitRange,
)

RESUME_TEXT = """
Sam Rivera | sam.rivera@email.com

EXPERIENCE
AI Transformation Director | Enterprise Inc | 2019 – Present
• Owned enterprise AI strategy and target operating model for GenAI adoption
• Directed organizational transformation across 8 business units
• Established AI center of excellence and enterprise AI portfolio execution
• Executive steering committee chair for AI transformation and change management
• Enterprise AI operating model and use case portfolio at scale

Director, Digital Transformation | Prior Co | 2014 – 2019
• Business transformation and operating model redesign

SKILLS
AI strategy, AI transformation, GenAI, responsible AI, operating model, transformation, MLOps
"""

FIXTURE = BenchmarkResumeFixture(
    fixture_id="ai_transformation_director",
    resume_text=RESUME_TEXT,
    expected_primary=RoleFamilyId.AI_TRANSFORMATION,
    expected_adjacent=(
        RoleFamilyId.AI_PROGRAM_MANAGEMENT,
        RoleFamilyId.DIGITAL_TRANSFORMATION,
        RoleFamilyId.TRANSFORMATION_OFFICE,
    ),
    forbidden_families=(
        RoleFamilyId.AI_GOVERNANCE,
        RoleFamilyId.SOFTWARE_ENGINEERING,
        RoleFamilyId.HR,
    ),
    excluded_families=(),
    capability_traits=(
        CapabilityTraitRange("ai_strategy", 0.12, 0.60),
        CapabilityTraitRange("transformation_strategy", 0.10, 0.55),
        CapabilityTraitRange("change_management", 0.08, 0.50),
        CapabilityTraitRange("engineering_depth", 0.0, 0.30),
    ),
    description="AI transformation executive; AI governance must not outrank transformation.",
)
