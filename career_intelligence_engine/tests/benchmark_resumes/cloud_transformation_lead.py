"""Benchmark: cloud transformation lead."""

from __future__ import annotations

from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.tests.benchmark_resumes.schema import (
    BenchmarkResumeFixture,
    CapabilityTraitRange,
)

RESUME_TEXT = """
Chris Hale | chris.hale@email.com

EXPERIENCE
Cloud Transformation Lead | CloudFirst | 2018 – Present
• Led enterprise cloud migration and cloud transformation program across AWS and Azure
• Landing zone design, multi-cloud strategy, FinOps, and cloud program governance
• Kubernetes and terraform platform standards for migration waves
• Executive steering for cloud migration portfolio and benefits tracking

Cloud Program Manager | MigrateCo | 2013 – 2018
• Cloud migration director responsibilities and technical program coordination

SKILLS
AWS, Azure, GCP, kubernetes, terraform, cloud migration, landing zone, FinOps, multi-cloud
"""

FIXTURE = BenchmarkResumeFixture(
    fixture_id="cloud_transformation_lead",
    resume_text=RESUME_TEXT,
    expected_primary=RoleFamilyId.CLOUD_TRANSFORMATION,
    expected_adjacent=(
        RoleFamilyId.TECHNICAL_PROGRAM_MANAGEMENT,
    ),
    forbidden_families=(
        RoleFamilyId.AI_GOVERNANCE,
        RoleFamilyId.HR,
        RoleFamilyId.PRODUCT_MANAGEMENT,
    ),
    excluded_families=(),
    capability_traits=(
        CapabilityTraitRange("transformation_strategy", 0.08, 0.50),
        CapabilityTraitRange("technical_execution", 0.08, 0.50),
        CapabilityTraitRange("architecture_coordination", 0.0, 0.45),
        CapabilityTraitRange("product_thinking", 0.0, 0.20),
    ),
    description="Cloud migration/transformation lead with platform vocabulary.",
)
