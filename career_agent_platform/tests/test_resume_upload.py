"""Phase 5A resume upload extraction tests (PDF, DOCX, TXT)."""

from __future__ import annotations

import pytest

from career_intelligence_engine.tests.fixtures.calibration_resumes import RESUME_TPM
from career_intelligence_engine.tests.fixtures.sample_jds import JD_TPM
from job_sources.generic_job_parser import GenericJobParser
from recommendation_engine import RecommendationEngine
from resume_extraction import extract_resume_from_upload
from tests.fixtures.resume_upload_fixtures import make_docx_bytes, make_pdf_bytes


@pytest.fixture
def engine() -> RecommendationEngine:
    return RecommendationEngine()


def test_pdf_resume_upload() -> None:
    content = make_pdf_bytes("Jordan Chen\nSenior Technical Program Manager")
    result = extract_resume_from_upload("resume.pdf", content)
    assert result.success
    assert "Jordan Chen" in result.resume_text
    assert "Technical Program Manager" in result.resume_text


def test_docx_resume_upload() -> None:
    content = make_docx_bytes(RESUME_TPM)
    result = extract_resume_from_upload("resume.docx", content)
    assert result.success
    assert "Jordan Chen" in result.resume_text
    assert "Technical Program Manager" in result.resume_text


def test_empty_resume_upload() -> None:
    empty_txt = extract_resume_from_upload("empty.txt", b"")
    assert not empty_txt.success
    assert empty_txt.error_reason == "empty_extraction"

    whitespace_txt = extract_resume_from_upload("spaces.txt", b"   \n\t  ")
    assert not whitespace_txt.success
    assert whitespace_txt.error_reason == "empty_extraction"

    empty_pdf = extract_resume_from_upload("empty.pdf", b"")
    assert not empty_pdf.success
    assert empty_pdf.error_reason == "empty_extraction"

    corrupt_pdf = extract_resume_from_upload("bad.pdf", b"not-a-valid-pdf")
    assert not corrupt_pdf.success
    assert corrupt_pdf.error_reason in ("corrupted_pdf", "parsing_failure")

    unsupported = extract_resume_from_upload("resume.rtf", b"data")
    assert not unsupported.success
    assert unsupported.error_reason == "unsupported_file"


def test_resume_text_population(engine: RecommendationEngine) -> None:
    """Uploaded resume text feeds RecommendationEngine without manual paste."""
    pdf = make_pdf_bytes(RESUME_TPM)
    extracted = extract_resume_from_upload("candidate.pdf", pdf)
    assert extracted.success

    parser = GenericJobParser()
    posting = parser.parse_pasted_text(JD_TPM, job_id="tpm_upload", title="TPM", company="Global")
    profile, recs = engine.recommend_from_resume(extracted.resume_text, [posting])
    assert profile.full_name or "Jordan" in extracted.resume_text
    assert len(recs) == 1
    assert recs[0].job_id == "tpm_upload"
    assert recs[0].overall_match > 0
