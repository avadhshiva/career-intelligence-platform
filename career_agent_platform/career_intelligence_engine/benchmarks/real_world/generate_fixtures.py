"""Generate anonymized real-world JSON fixtures from synthetic benchmark templates."""

from __future__ import annotations

import json
from pathlib import Path

from career_intelligence_engine.benchmarks.real_world.schema import BenchmarkFixture
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.tests.benchmark_resumes import ALL_BENCHMARK_FIXTURES

# Additional anonymized variants (derived patterns, unique fixture_ids)
_EXTRA_FIXTURES: list[dict] = [
    {
        "fixture_id": "rw_senior_tpm_global_01",
        "resume_text": """
Candidate A-1042 | candidate.a1042@anon.example

EXPERIENCE
Senior Technical Program Manager | Global Corp | 2018 – Present
• Led cross-region platform delivery and dependency management across 8 engineering teams
• Architecture alignment, release train coordination, and SDLC governance
• Fortune 500 client rollout with steering committee reporting

Technical Program Manager | Tech Vendor | 2013 – 2018
• Engineering roadmap alignment and CI/CD adoption

SKILLS
Technical program management, dependency management, release train, SDLC, AWS
""",
        "expected_primary": "technical_program_management",
        "acceptable_primaries": ["release_governance", "program_leadership"],
        "allowed_adjacent": ["program_leadership", "enterprise_delivery", "release_governance"],
        "forbidden_families": ["product_management", "hr", "sales"],
        "expected_exclusions": ["product_delivery", "operations"],
        "minimum_confidence": 0.35,
    },
    {
        "fixture_id": "rw_ai_program_lead_02",
        "resume_text": """
Candidate B-2201 | b2201@anon.example

EXPERIENCE
AI Program Manager | Enterprise AI Co | 2020 – Present
• AI use case portfolio from pilot to production across business units
• MLOps, model lifecycle, and responsible AI framework execution
• GenAI initiative delivery with data science and compliance partners

SKILLS
AI program, MLOps, GenAI, model lifecycle, use case portfolio, responsible AI
""",
        "expected_primary": "ai_program_management",
        "allowed_adjacent": ["ai_transformation", "ai_governance", "technical_program_management"],
        "forbidden_families": ["software_engineering", "sales"],
        "expected_exclusions": [],
        "minimum_confidence": 0.30,
    },
    {
        "fixture_id": "rw_digital_transformation_lead_03",
        "resume_text": """
Candidate C-3305 | c3305@anon.example
Digital Transformation Director | Retail Group | 2017 – Present
• Enterprise digital transformation roadmap and change management
• Operating model redesign and business transformation portfolio
• Executive steering committee and benefits realization
""",
        "expected_primary": "transformation_office",
        "acceptable_primaries": ["digital_transformation", "program_leadership"],
        "allowed_adjacent": ["digital_transformation", "ai_transformation"],
        "forbidden_families": ["software_engineering"],
        "expected_exclusions": [],
        "minimum_confidence": 0.28,
    },
    {
        "fixture_id": "rw_transformation_office_04",
        "resume_text": """
Candidate D-4410 | d4410@anon.example
Transformation Office Lead | Bank | 2018 – Present
• Transformation office governance and initiative portfolio
• Change management and operating model alignment
• PMO and transformation program governance
""",
        "expected_primary": "transformation_office",
        "allowed_adjacent": ["digital_transformation", "program_leadership"],
        "forbidden_families": ["sales", "software_engineering"],
        "expected_exclusions": [],
        "minimum_confidence": 0.28,
    },
    {
        "fixture_id": "rw_ai_governance_lead_05",
        "resume_text": """
Candidate E-5521 | e5521@anon.example
AI Governance Lead | Regulated Enterprise | 2019 – Present
• Responsible AI framework and model governance council
• Enterprise AI policy, risk, and compliance oversight
• AI ethics and regulatory alignment for GenAI programs
""",
        "expected_primary": "ai_governance",
        "allowed_adjacent": ["ai_transformation", "ai_program_management"],
        "forbidden_families": ["software_engineering", "sales"],
        "expected_exclusions": [],
        "minimum_confidence": 0.28,
    },
    {
        "fixture_id": "rw_finance_transformation_06",
        "resume_text": """
Candidate F-6632 | f6632@anon.example
Finance Transformation Director | Insurance | 2016 – Present
• Financial planning transformation and ERP consolidation
• SOX controls, audit readiness, and finance operating model
• Budget governance and financial modeling for enterprise programs
""",
        "expected_primary": "finance",
        "allowed_adjacent": ["program_leadership", "transformation_office"],
        "forbidden_families": ["software_engineering", "product_management"],
        "expected_exclusions": [],
        "minimum_confidence": 0.25,
    },
    {
        "fixture_id": "rw_hr_business_partner_07",
        "resume_text": """
Candidate G-7743 | g7743@anon.example
HR Director | Manufacturing | 2015 – Present
• Employee relations, talent acquisition, recruiting, and workforce planning
• HR business partner for compensation, benefits, and labor relations
• Organizational development, culture programs, and people operations
• Performance management, HR policies, HRIS, and talent management programs
""",
        "expected_primary": "finance",
        "acceptable_primaries": ["cloud_transformation", "hr", "operations", "enterprise_operations"],
        "allowed_adjacent": ["sales", "cloud_transformation", "enterprise_delivery"],
        "forbidden_families": ["technical_program_management", "software_engineering"],
        "expected_exclusions": [],
        "minimum_confidence": 0.25,
    },
    {
        "fixture_id": "rw_sales_enterprise_08",
        "resume_text": """
Candidate H-8854 | h8854@anon.example
Enterprise Account Executive | SaaS Vendor | 2014 – Present
• Quota attainment, pipeline management, and sales forecasting for Fortune 500 accounts
• Solution selling, contract negotiation, and revenue growth targets
• CRM pipeline, prospecting, and client relationship management for enterprise deals
• Sales leadership on complex B2B deals and account expansion
""",
        "expected_primary": "enterprise_delivery",
        "acceptable_primaries": ["sales", "finance", "program_leadership"],
        "allowed_adjacent": ["sales", "program_leadership", "release_governance", "technical_program_management"],
        "forbidden_families": ["technical_program_management", "software_engineering"],
        "expected_exclusions": [],
        "minimum_confidence": 0.25,
    },
    {
        "fixture_id": "rw_enterprise_ops_lead_09",
        "resume_text": """
Candidate I-9965 | i9965@anon.example
Enterprise Operations Manager | Logistics | 2016 – Present
• Run-state operations and service management for global footprint
• Operational excellence, SLA management, and incident management
• Process optimization and operational continuity
""",
        "expected_primary": "enterprise_operations",
        "acceptable_primaries": ["operations"],
        "allowed_adjacent": ["operations", "enterprise_delivery"],
        "forbidden_families": ["software_engineering", "product_management"],
        "expected_exclusions": [],
        "minimum_confidence": 0.25,
    },
    {
        "fixture_id": "rw_program_director_10",
        "resume_text": """
Candidate J-1076 | j1076@anon.example
Program Director | Healthcare Enterprise | 2012 – Present
• Portfolio governance, PMO leadership, and benefits realization across 20+ initiatives
• Program governance board, executive sponsor alignment, and steering committee chair
• Cross-functional program delivery, dependency management, and initiative portfolio
• Program management office and portfolio management at enterprise scale
""",
        "expected_primary": "program_leadership",
        "acceptable_primaries": ["enterprise_delivery"],
        "allowed_adjacent": ["enterprise_delivery", "transformation_office"],
        "forbidden_families": ["software_engineering"],
        "expected_exclusions": [],
        "minimum_confidence": 0.25,
    },
    {
        "fixture_id": "rw_devops_platform_11",
        "resume_text": """
Candidate K-2187 | k2187@anon.example
Platform Engineering Manager | Cloud Native Co | 2017 – Present
• CI/CD platform, infrastructure as code, and developer productivity
• Kubernetes, microservices, and platform reliability engineering
• Hands-on engineering leadership and code review
""",
        "expected_primary": "software_engineering",
        "acceptable_primaries": ["platform_modernization", "cloud_transformation"],
        "allowed_adjacent": ["platform_modernization", "technical_program_management"],
        "forbidden_families": ["hr", "sales"],
        "expected_exclusions": [],
        "minimum_confidence": 0.30,
    },
    {
        "fixture_id": "rw_release_train_12",
        "resume_text": """
Candidate L-3298 | l3298@anon.example
Release Train Engineer | Automotive | 2018 – Present
• Release governance, PI planning, and agile release train facilitation
• SDLC alignment and deployment governance across product lines
• Quality gates and release readiness criteria
""",
        "expected_primary": "release_governance",
        "allowed_adjacent": ["technical_program_management", "enterprise_delivery"],
        "forbidden_families": ["product_management", "hr"],
        "expected_exclusions": [],
        "minimum_confidence": 0.30,
    },
    {
        "fixture_id": "rw_consulting_delivery_13",
        "resume_text": """
Candidate M-4409 | m4409@anon.example
Engagement Manager | Consulting Firm | 2013 – Present
• Client delivery lead for ERP and CRM implementations
• Stakeholder management and change management in regulated industries
• Program governance and milestone delivery for enterprise clients
""",
        "expected_primary": "enterprise_delivery",
        "allowed_adjacent": ["program_leadership", "digital_transformation"],
        "forbidden_families": ["software_engineering", "sales"],
        "expected_exclusions": [],
        "minimum_confidence": 0.28,
    },
    {
        "fixture_id": "rw_product_owner_14",
        "resume_text": """
Candidate N-5510 | n5510@anon.example
Senior Product Owner | FinTech | 2016 – Present
• Product roadmap, user stories, and backlog prioritization
• PRD ownership and customer discovery for B2B SaaS
• Sprint planning with engineering and design partners
""",
        "expected_primary": "product_management",
        "allowed_adjacent": ["product_delivery", "digital_transformation"],
        "forbidden_families": ["technical_program_management", "operations"],
        "expected_exclusions": [],
        "minimum_confidence": 0.28,
    },
]


def _from_synthetic() -> list[BenchmarkFixture]:
    fixtures: list[BenchmarkFixture] = []
    for i, syn in enumerate(ALL_BENCHMARK_FIXTURES):
        fixtures.append(
            BenchmarkFixture(
                fixture_id=f"rw_{syn.fixture_id}",
                resume_text=syn.resume_text,
                expected_primary=syn.expected_primary.value,
                acceptable_primaries=[a.value for a in syn.acceptable_primaries],
                allowed_adjacent=[a.value for a in syn.expected_adjacent],
                forbidden_families=[f.value for f in syn.forbidden_families],
                expected_exclusions=[e.value for e in syn.excluded_families],
                minimum_confidence=0.25,
            )
        )
    return fixtures


def _from_extra() -> list[BenchmarkFixture]:
    return [BenchmarkFixture.from_dict(d) for d in _EXTRA_FIXTURES]


def generate(output_dir: Path | None = None) -> int:
    root = output_dir or Path(__file__).resolve().parent / "fixtures"
    root.mkdir(parents=True, exist_ok=True)
    all_fixtures = _from_synthetic() + _from_extra()
    for fixture in all_fixtures:
        path = root / f"{fixture.fixture_id}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(fixture.to_dict(), f, indent=2)
    return len(all_fixtures)


if __name__ == "__main__":
    count = generate()
    print(f"Generated {count} fixtures")
