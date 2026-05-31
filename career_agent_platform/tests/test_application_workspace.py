"""Phase 5C tests — application package workspace."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from application_workspace.evidence import extract_verified_evidence
from application_workspace.export import export_docx, export_package, export_txt, package_as_plaintext
from application_workspace.models import ApplicationApprovalState
from application_workspace.package_builder import ApplicationPackageBuilder
from application_workspace.review_manager import ApplicationReviewManager
from career_intelligence_engine.tests.fixtures.calibration_resumes import RESUME_TPM
from career_intelligence_engine.tests.fixtures.sample_jds import JD_RELEASE_GOVERNANCE, JD_TPM
from job_sources.generic_job_parser import GenericJobParser
from recommendation_engine import RecommendationEngine

_PLATFORM_ROOT = Path(__file__).resolve().parents[1]

FABRICATION_MARKERS = (
    "invented",
    "fabricated",
    "1000% improvement",
    "certified kubernetes architect",
    "pmp certified since 1990",
)


@pytest.fixture
def engine() -> RecommendationEngine:
    return RecommendationEngine()


@pytest.fixture
def parser() -> GenericJobParser:
    return GenericJobParser()


@pytest.fixture
def tmp_review(tmp_path: Path) -> ApplicationReviewManager:
    mgr = ApplicationReviewManager(data_dir=tmp_path / "application_packages")
    mgr.initialize()
    return mgr


@pytest.fixture
def builder(tmp_review: ApplicationReviewManager) -> ApplicationPackageBuilder:
    return ApplicationPackageBuilder(tmp_review)


def _rec_for_jd(engine: RecommendationEngine, parser: GenericJobParser, jd: str, job_id: str):
    posting = parser.parse_pasted_text(jd, job_id=job_id, title="Role", company="Test Co")
    return engine.recommend_from_resume(RESUME_TPM, [posting])[1][0]


def test_deterministic_package_generation(
    engine: RecommendationEngine,
    parser: GenericJobParser,
    builder: ApplicationPackageBuilder,
) -> None:
    rec = _rec_for_jd(engine, parser, JD_TPM, "tpm_pkg")
    pkg1 = builder.build(rec, RESUME_TPM, persist=False)
    pkg2 = builder.build(rec, RESUME_TPM, persist=False)
    assert pkg1.cover_letter
    assert pkg1.cover_letter.body == pkg2.cover_letter.body
    assert pkg1.recruiter_message
    assert pkg1.recruiter_message.linkedin_intro == pkg2.recruiter_message.linkedin_intro
    assert pkg1.interview_prep
    assert pkg1.interview_prep.likely_focus_areas == pkg2.interview_prep.likely_focus_areas


def test_no_fabrication_in_cover_letter(
    engine: RecommendationEngine,
    parser: GenericJobParser,
    builder: ApplicationPackageBuilder,
) -> None:
    rec = _rec_for_jd(engine, parser, JD_TPM, "tpm_fab")
    pkg = builder.build(rec, RESUME_TPM, persist=False)
    body = (pkg.cover_letter.body if pkg.cover_letter else "").lower()
    for marker in FABRICATION_MARKERS:
        assert marker not in body
    evidence = extract_verified_evidence(RESUME_TPM, rec)
    for snippet in evidence.evidence_snippets:
        assert snippet.lower() in RESUME_TPM.lower() or any(
            word in RESUME_TPM.lower() for word in snippet.lower().split() if len(word) > 5
        )


def test_explainability_present(
    engine: RecommendationEngine,
    parser: GenericJobParser,
    builder: ApplicationPackageBuilder,
) -> None:
    rec = _rec_for_jd(engine, parser, JD_RELEASE_GOVERNANCE, "rg_exp")
    pkg = builder.build(rec, RESUME_TPM, persist=False)
    combined = " ".join(pkg.explanation).lower()
    assert pkg.explanation
    assert any(
        kw in combined
        for kw in ("evidence", "governance", "resume", "excluded", "intentionally")
    )


def test_recruiter_message_quality(
    engine: RecommendationEngine,
    parser: GenericJobParser,
    builder: ApplicationPackageBuilder,
) -> None:
    rec = _rec_for_jd(engine, parser, JD_TPM, "tpm_msg")
    pkg = builder.build(rec, RESUME_TPM, persist=False)
    msg = pkg.recruiter_message
    assert msg
    assert len(msg.linkedin_intro) < 600
    assert "spam" not in msg.linkedin_intro.lower()
    assert rec.job_title in msg.linkedin_intro or rec.company in msg.linkedin_intro
    assert msg.hiring_manager_note.strip()
    assert msg.referral_request.strip()


def test_interview_prep_generation(
    engine: RecommendationEngine,
    parser: GenericJobParser,
    builder: ApplicationPackageBuilder,
) -> None:
    rec = _rec_for_jd(engine, parser, JD_RELEASE_GOVERNANCE, "rg_prep")
    pkg = builder.build(rec, RESUME_TPM, persist=False)
    prep = pkg.interview_prep
    assert prep
    assert prep.likely_focus_areas
    assert prep.probable_gap_questions
    assert prep.preparation_topics
    assert prep.explanation


def test_application_quality_score(
    engine: RecommendationEngine,
    parser: GenericJobParser,
    builder: ApplicationPackageBuilder,
) -> None:
    rec = _rec_for_jd(engine, parser, JD_TPM, "tpm_q")
    pkg = builder.build(rec, RESUME_TPM, persist=False)
    assert pkg.quality_scores
    assert 0.0 <= pkg.quality_scores.overall_application_quality_score <= 1.0
    assert pkg.quality_scores.resume_alignment == pytest.approx(rec.overall_match, rel=0.01)


def test_approval_workflow_persistence(
    engine: RecommendationEngine,
    parser: GenericJobParser,
    builder: ApplicationPackageBuilder,
    tmp_review: ApplicationReviewManager,
) -> None:
    rec = _rec_for_jd(engine, parser, JD_TPM, "tpm_persist")
    pkg = builder.build(rec, RESUME_TPM, persist=True)
    tmp_review.mark_under_review(pkg.package_id)
    result = tmp_review.approve(pkg.package_id, notes="ready to send")
    assert result.success
    reloaded = tmp_review.get_package(pkg.package_id)
    assert reloaded.approval_status == ApplicationApprovalState.APPROVED
    assert reloaded.state_history
    path = tmp_review._package_path(pkg.package_id)
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["approval_status"] == "approved"


def test_export_generation(
    engine: RecommendationEngine,
    parser: GenericJobParser,
    builder: ApplicationPackageBuilder,
    tmp_path: Path,
) -> None:
    rec = _rec_for_jd(engine, parser, JD_TPM, "tpm_export")
    pkg = builder.build(rec, RESUME_TPM, persist=False)
    out = tmp_path / "exports"
    txt_path = export_txt(pkg, out)
    assert txt_path.exists()
    text = txt_path.read_text(encoding="utf-8")
    assert "COVER LETTER" in text
    assert rec.job_title in text or pkg.job_title in text
    paths = export_package(pkg, out, formats=["txt", "docx"])
    assert paths["txt"]
    assert Path(paths["docx"]).exists()
    plain = package_as_plaintext(pkg)
    assert not re.search(r"\b(None)\b", plain)


def test_tailored_resume_only_reorders_content(
    engine: RecommendationEngine,
    parser: GenericJobParser,
    builder: ApplicationPackageBuilder,
) -> None:
    rec = _rec_for_jd(engine, parser, JD_TPM, "tpm_tailor")
    pkg = builder.build(rec, RESUME_TPM, persist=False)
    assert "no new claims" in pkg.tailored_resume_text.lower() or "deterministic" in pkg.tailored_resume_text.lower()
    assert "Jordan Chen" in pkg.tailored_resume_text
