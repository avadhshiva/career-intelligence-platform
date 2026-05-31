"""Representative benchmark resume fixtures for ontology calibration."""

from __future__ import annotations

from career_intelligence_engine.tests.benchmark_resumes.ai_transformation_director import (
    FIXTURE as AI_TRANSFORMATION_DIRECTOR,
)
from career_intelligence_engine.tests.benchmark_resumes.cloud_transformation_lead import (
    FIXTURE as CLOUD_TRANSFORMATION_LEAD,
)
from career_intelligence_engine.tests.benchmark_resumes.enterprise_architect import (
    FIXTURE as ENTERPRISE_ARCHITECT,
)
from career_intelligence_engine.tests.benchmark_resumes.enterprise_delivery_manager import (
    FIXTURE as ENTERPRISE_DELIVERY_MANAGER,
)
from career_intelligence_engine.tests.benchmark_resumes.operations_manager import (
    FIXTURE as OPERATIONS_MANAGER,
)
from career_intelligence_engine.tests.benchmark_resumes.platform_modernization_lead import (
    FIXTURE as PLATFORM_MODERNIZATION_LEAD,
)
from career_intelligence_engine.tests.benchmark_resumes.product_delivery_lead import (
    FIXTURE as PRODUCT_DELIVERY_LEAD,
)
from career_intelligence_engine.tests.benchmark_resumes.product_manager_b2c import (
    FIXTURE as PRODUCT_MANAGER_B2C,
)
from career_intelligence_engine.tests.benchmark_resumes.program_leadership_enterprise import (
    FIXTURE as PROGRAM_LEADERSHIP_ENTERPRISE,
)
from career_intelligence_engine.tests.benchmark_resumes.release_governance_lead import (
    FIXTURE as RELEASE_GOVERNANCE_LEAD,
)
from career_intelligence_engine.tests.benchmark_resumes.schema import (
    BenchmarkResumeFixture,
    CapabilityTraitRange,
)
from career_intelligence_engine.tests.benchmark_resumes.software_engineering_manager import (
    FIXTURE as SOFTWARE_ENGINEERING_MANAGER,
)
from career_intelligence_engine.tests.benchmark_resumes.technical_program_manager_enterprise import (
    FIXTURE as TECHNICAL_PROGRAM_MANAGER_ENTERPRISE,
)

ALL_BENCHMARK_FIXTURES: tuple[BenchmarkResumeFixture, ...] = (
    TECHNICAL_PROGRAM_MANAGER_ENTERPRISE,
    PROGRAM_LEADERSHIP_ENTERPRISE,
    RELEASE_GOVERNANCE_LEAD,
    PRODUCT_MANAGER_B2C,
    ENTERPRISE_ARCHITECT,
    SOFTWARE_ENGINEERING_MANAGER,
    CLOUD_TRANSFORMATION_LEAD,
    AI_TRANSFORMATION_DIRECTOR,
    OPERATIONS_MANAGER,
    ENTERPRISE_DELIVERY_MANAGER,
    PLATFORM_MODERNIZATION_LEAD,
    PRODUCT_DELIVERY_LEAD,
)

BENCHMARK_FIXTURE_BY_ID: dict[str, BenchmarkResumeFixture] = {
    f.fixture_id: f for f in ALL_BENCHMARK_FIXTURES
}

__all__ = [
    "ALL_BENCHMARK_FIXTURES",
    "BENCHMARK_FIXTURE_BY_ID",
    "BenchmarkResumeFixture",
    "CapabilityTraitRange",
]
