"""Benchmark: enterprise delivery / implementation manager."""

from __future__ import annotations

from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.tests.benchmark_resumes.schema import (
    BenchmarkResumeFixture,
    CapabilityTraitRange,
)

RESUME_TEXT = """
Jamie Fox | jamie.fox@email.com

EXPERIENCE
Enterprise Delivery Manager | ConsultCo | 2015 – Present
• Led global rollout of ERP implementation across multi-geography client engagements
• CRM implementation and SI partner management with change management
• Client delivery governance and implementation lead for Fortune 500 accounts
• Program steering and benefits realization for enterprise delivery portfolio

Implementation Lead | Global SI | 2009 – 2015
• Client delivery, hypercare, and delivery governance

SKILLS
ERP implementation, CRM implementation, change management, client delivery, global rollout, SI partner
"""

FIXTURE = BenchmarkResumeFixture(
    fixture_id="enterprise_delivery_manager",
    resume_text=RESUME_TEXT,
    expected_primary=RoleFamilyId.ENTERPRISE_DELIVERY,
    expected_adjacent=(
        RoleFamilyId.PROGRAM_LEADERSHIP,
        RoleFamilyId.DIGITAL_TRANSFORMATION,
    ),
    forbidden_families=(
        RoleFamilyId.PRODUCT_MANAGEMENT,
        RoleFamilyId.SOFTWARE_ENGINEERING,
        RoleFamilyId.HR,
    ),
    excluded_families=(),
    capability_traits=(
        CapabilityTraitRange("delivery_execution", 0.12, 0.65),
        CapabilityTraitRange("change_management", 0.08, 0.50),
        CapabilityTraitRange("stakeholder_complexity", 0.05, 0.45),
        CapabilityTraitRange("product_thinking", 0.0, 0.22),
    ),
    description="SI-style enterprise delivery lead; product management must not dominate.",
)
