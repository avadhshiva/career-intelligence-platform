"""First-class job entity normalization layer tests."""

from __future__ import annotations

from job_sources.company_registry import ENTERPRISE_FALLBACK_NAME, resolve_company
from job_sources.generic_job_parser import GenericJobParser
from job_sources.industry_mapper import infer_industry
from job_sources.location_inference import infer_location
from job_sources.normalization import (
    ENTITY_VERSION,
    NormalizedJobPosting,
    apply_normalization_to_recommendation,
    build_job_entity,
    normalize_job_posting,
    pretty_job_label,
)
from job_sources.title_normalization import normalize_title
from recommendation_engine import RecommendationEngine


def test_noisy_title_tmp_id() -> None:
    result = normalize_title(
        title="Tmp5Roiq3Fw",
        raw_text="Lead enterprise program governance across portfolio teams.",
    )
    assert "tmp" not in result.normalized_title.lower()
    assert "Program" in result.normalized_title or "Leadership" in result.normalized_title


def test_title_abbreviation_expansion() -> None:
    result = normalize_title(
        title="Sr TPM - AI/ML",
        raw_text="Technical program manager for platform delivery.",
    )
    assert "Senior" in result.normalized_title
    assert "Technical Program Manager" in result.normalized_title


def test_title_director_program() -> None:
    result = normalize_title(title="Dir Prog Mgmt", raw_text="Program director for enterprise delivery.")
    assert "Director" in result.normalized_title
    assert "Program" in result.normalized_title


def test_company_alias_jpmc() -> None:
    name, aliases, _ = resolve_company(company="Unknown", raw_text="JPMC is hiring in Bengaluru.")
    assert name == "JP Morgan Chase"
    assert "jpmc" in aliases or any("jpm" in a for a in aliases)


def test_company_walmart_gcc() -> None:
    name, _, company_type = resolve_company(
        company="",
        raw_text="Walmart GCC is expanding TPM hiring in Bangalore.",
    )
    assert name == "Walmart Global Tech"
    assert company_type == "Retail Tech"


def test_missing_company_fallback() -> None:
    name, _, _ = resolve_company(company="Unknown", raw_text="Generic enterprise role without employer name.")
    assert name == ENTERPRISE_FALLBACK_NAME
    assert name.lower() != "unknown"


def test_location_bangalore_and_hybrid() -> None:
    loc = infer_location(location="", raw_text="Based in Bangalore. Hybrid work model available.")
    assert loc.location == "Bangalore"
    assert loc.remote_type == "Hybrid"


def test_us_remote() -> None:
    loc = infer_location(location="", raw_text="US Remote role for platform TPM.")
    assert loc.remote_type == "US Remote"


def test_industry_retail_from_jd() -> None:
    industry = infer_industry(
        company_type="Global Enterprise",
        company_name="",
        raw_text="Retail technology transformation program.",
    )
    assert industry == "Retail Tech"


def test_entity_has_full_schema() -> None:
    entity = build_job_entity(
        job_id="job-1",
        raw_title="TmpABC",
        company="Unknown",
        location="",
        raw_text="ServiceNow release governance lead in Bengaluru. Hybrid. recruiter: Jane Smith jane@servicenow.com",
        source="generic",
    )
    assert entity.job_id == "job-1"
    assert entity.entity_version == ENTITY_VERSION
    assert entity.normalized_title
    assert entity.company_name == "ServiceNow"
    assert entity.clean_display_label
    assert entity.recommendation_label
    assert entity.normalized_summary
    assert entity.confidence > 0
    assert "@" in entity.recruiter_contact or entity.recruiter_name


def test_summary_generation_deterministic() -> None:
    entity = build_job_entity(
        job_id="j2",
        raw_title="Senior TPM",
        company="Walmart Global Tech",
        location="Bangalore",
        raw_text="Enterprise AI delivery and release governance for retail technology.",
        source="imported",
        role_family_hint="technical_program_management",
    )
    again = build_job_entity(
        job_id="j2",
        raw_title="Senior TPM",
        company="Walmart Global Tech",
        location="Bangalore",
        raw_text="Enterprise AI delivery and release governance for retail technology.",
        source="imported",
        role_family_hint="technical_program_management",
    )
    assert entity.normalized_summary == again.normalized_summary
    assert "retail" in entity.normalized_summary.lower() or "delivery" in entity.normalized_summary.lower()


def test_normalize_job_posting_integration() -> None:
    parser = GenericJobParser()
    posting = parser.parse_pasted_text(
        "Accenture is hiring a Release Governance Lead in Hyderabad. Full-time. Remote optional.",
        job_id="x1",
        title="Tmpmczox2J2",
        company="Unknown",
    )
    entity = normalize_job_posting(posting)
    assert entity.company_name == "Accenture"
    assert "tmp" not in entity.normalized_title.lower()


def test_apply_normalization_preserves_scores() -> None:
    engine = RecommendationEngine()
    parser = GenericJobParser()
    posting = parser.parse_pasted_text(
        "Technical program manager for platform delivery at JP Morgan in London.",
        job_id="j1",
        title="TmpABC123",
        company="Unknown",
    )
    profile, recs = engine.recommend_from_resume(
        "Jordan Chen\nSenior Technical Program Manager\nRelease governance\nJP Morgan",
        [posting],
    )
    rec = recs[0]
    before_match = rec.overall_match
    before_conf = rec.confidence
    entity = apply_normalization_to_recommendation(rec, raw_text=posting.raw_text, posting=posting)
    assert rec.overall_match == before_match
    assert rec.confidence == before_conf
    assert rec.company not in ("Unknown", "")
    assert rec.match_detail.get("job_entity")
    assert rec.match_detail["job_entity"]["entity_version"] == ENTITY_VERSION


def test_pretty_job_label_uses_display_label() -> None:
    entity = build_job_entity(
        job_id="d1",
        raw_title="Senior Technical Program Manager",
        company="Walmart Global Tech",
        location="Bangalore",
        raw_text="",
        source="imported",
    )
    label = pretty_job_label(normalized=entity)
    assert "Walmart Global Tech" in label
    assert "Senior Technical Program Manager" in label


def test_entity_roundtrip_json() -> None:
    entity = build_job_entity(
        job_id="r1",
        raw_title="TPM",
        company="Microsoft",
        location="Seattle",
        raw_text="Cloud platform TPM",
        source="linkedin",
    )
    restored = NormalizedJobPosting.from_dict(entity.to_dict())
    assert restored.normalized_title == entity.normalized_title
    assert restored.clean_title == entity.normalized_title
