"""Resume persistence and session restoration."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence_engine.tests.fixtures.calibration_resumes import RESUME_TPM
from recommendation_engine import RecommendationEngine
from resume_store.models import ResumeIdentity
from resume_store.session_manager import (
    build_resume_identity,
    get_active_resume,
    persist_and_activate_resume,
)
from resume_store.storage import ResumeStore, compute_resume_id


@pytest.fixture
def store(tmp_path: Path) -> ResumeStore:
    return ResumeStore(root=tmp_path / "resumes")


def test_compute_resume_id_stable() -> None:
    a = compute_resume_id(raw_text="hello\nworld")
    b = compute_resume_id(raw_text="hello\nworld")
    assert a == b
    assert len(a) == 16


def test_save_and_load_resume(store: ResumeStore) -> None:
    engine = RecommendationEngine()
    profile = engine.analyze_resume(RESUME_TPM)
    identity = build_resume_identity(filename="tpm.pdf", raw_text=RESUME_TPM, profile=profile)
    store.save(identity)
    loaded = store.load(identity.resume_id)
    assert loaded is not None
    assert loaded.filename == "tpm.pdf"
    assert loaded.primary_role_family == profile.primary_career_track.value
    assert loaded.raw_text == RESUME_TPM.strip()


def test_session_restores_active_resume(store: ResumeStore) -> None:
    engine = RecommendationEngine()
    profile = engine.analyze_resume(RESUME_TPM)
    identity = build_resume_identity(filename="resume.txt", raw_text=RESUME_TPM, profile=profile)
    session: dict = {}
    persist_and_activate_resume(session_state=session, store=store, identity=identity)
    result = get_active_resume(session, store=store)
    assert result.resume_id == identity.resume_id
    assert result.resume is not None
    assert result.resume.top_skills


def test_resume_identity_roundtrip_json() -> None:
    data = {
        "resume_id": "abc123",
        "filename": "f.pdf",
        "uploaded_at": "2026-01-01T00:00:00+00:00",
        "raw_text": "text",
        "parsed_profile_summary": "summary",
        "primary_role_family": "technical_program_management",
        "adjacent_roles": ["program_leadership"],
        "years_experience": 12.0,
        "dominant_dimensions": ["delivery"],
        "top_skills": ["TPM"],
        "ai_maturity": "pilot",
        "transformation_focus": 0.4,
        "recommended_resume_label": "TPM Resume",
    }
    identity = ResumeIdentity.from_dict(data)
    assert identity.to_dict()["resume_id"] == "abc123"
