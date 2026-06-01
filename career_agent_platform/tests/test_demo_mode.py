"""Read-only demo mode — persistence guards without scoring changes."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from career_intelligence_engine.tests.fixtures.calibration_resumes import RESUME_TPM
from job_sources.generic_job_parser import GenericJobParser
from recommendation_engine import RecommendationEngine
from review_queue_manager import ReviewQueueManager


@pytest.fixture
def demo_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAREER_AGENT_DEMO_MODE", "1")


def test_demo_mode_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify default behavior when demo mode is NOT enabled.

    CI may set CAREER_AGENT_DEMO_MODE=1 globally, so explicitly remove it
    to ensure this test validates the default state.
    """
    monkeypatch.delenv("CAREER_AGENT_DEMO_MODE", raising=False)

    from demo_mode import is_demo_mode, persistence_writes_enabled

    assert not is_demo_mode()
    assert persistence_writes_enabled()


def test_review_queue_skips_writes_in_demo_mode(demo_env: None, tmp_path: Path) -> None:
    from demo_mode import is_demo_mode

    assert is_demo_mode()
    path = tmp_path / "review_queue.json"
    path.write_text(json.dumps({"entries": []}), encoding="utf-8")

    mgr = ReviewQueueManager(data_dir=tmp_path)
    parser = GenericJobParser()

    from career_intelligence_engine.tests.fixtures.sample_jds import JD_TPM

    posting = parser.parse_pasted_text(
        JD_TPM,
        job_id="demo_q",
        title="TPM",
        company="Co",
    )

    _, recs = RecommendationEngine().recommend_from_resume(
        RESUME_TPM,
        [posting],
    )

    mgr.enqueue_many(recs)

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw.get("entries") == []


def test_demo_mode_import_smoke(demo_env: None) -> None:
    import Home  # noqa: F401
    from demo_mode import persistence_writes_enabled

    assert not persistence_writes_enabled()


def test_demo_mode_startup_no_exception(demo_env: None) -> None:
    os.environ["CAREER_AGENT_DEMO_MODE"] = "1"

    from resume_store.storage import CanonicalResumeStore, save_active_resume_id
    from application_workspace.review_manager import ApplicationReviewManager

    save_active_resume_id("demo-test-id")

    store = CanonicalResumeStore()
    mgr = ApplicationReviewManager(data_dir=Path("/tmp/unused-demo"))
    mgr.initialize()

    assert True