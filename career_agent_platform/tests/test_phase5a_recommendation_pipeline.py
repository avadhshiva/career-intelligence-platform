"""Phase 5A tests — ingestion, ranking, review queue, explainability, gating."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from career_intelligence_engine.tests.fixtures.calibration_resumes import RESUME_TPM
from career_intelligence_engine.tests.fixtures.sample_jds import (
    JD_OPERATIONS,
    JD_PRODUCT,
    JD_RELEASE_GOVERNANCE,
    JD_TPM,
)
from job_sources.generic_job_parser import GenericJobParser
from memory.decision_memory import DecisionMemory
from recommendation_engine import (
    RecommendationEngine,
    RecommendationPriority,
    RecommendationResult,
)
from review_queue_manager import QueueState, ReviewQueueManager
from workflows.recommendation_pipeline import PipelineInput, RecommendationPipeline

_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
_SAMPLE_FEED = _PLATFORM_ROOT / "data" / "sample_job_feed.json"


@pytest.fixture
def engine() -> RecommendationEngine:
    return RecommendationEngine()


@pytest.fixture
def parser() -> GenericJobParser:
    return GenericJobParser()


@pytest.fixture
def tmp_queue(tmp_path: Path) -> ReviewQueueManager:
    mgr = ReviewQueueManager(data_dir=tmp_path)
    mgr.initialize()
    return mgr


@pytest.fixture
def tmp_memory(tmp_path: Path) -> DecisionMemory:
    mem = DecisionMemory(data_dir=tmp_path)
    mem.initialize()
    return mem


def _postings_from_jds(parser: GenericJobParser, specs: list[tuple[str, str, str]]) -> list:
    out = []
    for job_id, title, jd in specs:
        out.append(parser.parse_pasted_text(jd, job_id=job_id, title=title, company="Test Co"))
    return out


def test_sample_feed_loads_five_jobs(parser: GenericJobParser) -> None:
    jobs = parser.parse_json_file(_SAMPLE_FEED)
    assert len(jobs) == 5
    assert {j.job_id for j in jobs} == {
        "sample_tpm_001",
        "sample_release_gov_001",
        "sample_enterprise_delivery_001",
        "sample_product_001",
        "sample_operations_001",
    }


def test_deterministic_ranking_stable(engine: RecommendationEngine, parser: GenericJobParser) -> None:
    postings = parser.parse_json_file(_SAMPLE_FEED)
    run1 = engine.recommend_from_resume(RESUME_TPM, postings)[1]
    run2 = engine.recommend_from_resume(RESUME_TPM, postings)[1]
    assert [r.job_id for r in run1] == [r.job_id for r in run2]
    assert [r.overall_match for r in run1] == [r.overall_match for r in run2]
    assert [r.recommendation_priority for r in run1] == [r.recommendation_priority for r in run2]


def test_tpm_resume_ranks_tpm_above_product(engine: RecommendationEngine, parser: GenericJobParser) -> None:
    postings = _postings_from_jds(
        parser,
        [
            ("j_product", "Product Manager", JD_PRODUCT),
            ("j_tpm", "TPM", JD_TPM),
        ],
    )
    recs = engine.recommend_from_resume(RESUME_TPM, postings)[1]
    by_id = {r.job_id: r for r in recs}
    assert by_id["j_tpm"].overall_match > by_id["j_product"].overall_match
    assert by_id["j_tpm"].recommendation_priority.value in (
        RecommendationPriority.STRONG_MATCH.value,
        RecommendationPriority.GOOD_MATCH.value,
        RecommendationPriority.BORDERLINE.value,
    )


def test_product_jd_gates_tpm_resume(engine: RecommendationEngine, parser: GenericJobParser) -> None:
    posting = parser.parse_pasted_text(JD_PRODUCT, job_id="prod", title="PM", company="SaaS")
    rec = engine.recommend_from_resume(RESUME_TPM, [posting])[1][0]
    assert not rec.eligibility_passed or rec.overall_match <= 0.55
    assert rec.recommendation_priority in (
        RecommendationPriority.BORDERLINE,
        RecommendationPriority.LOW_MATCH,
    )


def test_operations_jd_low_match_for_tpm_without_ops_evidence(
    engine: RecommendationEngine,
    parser: GenericJobParser,
) -> None:
    posting = parser.parse_pasted_text(JD_OPERATIONS, job_id="ops", title="Ops Mgr", company="Ops")
    rec = engine.recommend_from_resume(RESUME_TPM, [posting])[1][0]
    assert not rec.eligibility_passed or rec.overall_match < 0.50


def test_recommendation_explainability_fields(engine: RecommendationEngine, parser: GenericJobParser) -> None:
    posting = parser.parse_pasted_text(JD_RELEASE_GOVERNANCE, job_id="rg", title="Release Lead", company="Ent")
    rec = engine.recommend_from_resume(RESUME_TPM, [posting])[1][0]
    assert rec.recruiter_summary
    assert rec.why_matched or rec.why_not_matched
    assert rec.top_strengths is not None
    assert rec.top_risks is not None
    assert rec.missing_capabilities is not None
    assert rec.dominant_dimensions is not None
    assert rec.match_detail.get("scorer_path") == "deterministic_job_match_v1"


def test_approval_persistence(tmp_queue: ReviewQueueManager, engine: RecommendationEngine, parser: GenericJobParser) -> None:
    posting = parser.parse_pasted_text(JD_TPM, job_id="tpm", title="TPM", company="Global")
    rec = engine.recommend_from_resume(RESUME_TPM, [posting])[1][0]
    entry_id = tmp_queue.enqueue_recommendation(rec)
    tmp_queue.approve(entry_id, notes="good fit")
    approved = tmp_queue.list_approved()
    assert len(approved) == 1
    assert approved[0]["recommendation"]["approval_status"] == "approved"


def test_queue_transitions(tmp_queue: ReviewQueueManager, engine: RecommendationEngine, parser: GenericJobParser) -> None:
    posting = parser.parse_pasted_text(JD_TPM, job_id="tpm2", title="TPM", company="Global")
    rec = engine.recommend_from_resume(RESUME_TPM, [posting])[1][0]
    entry_id = tmp_queue.enqueue_recommendation(rec)
    tmp_queue.reject(entry_id, reason="low priority")
    assert len(tmp_queue.list_rejected()) == 1
    tmp_queue.archive(entry_id)
    assert len(tmp_queue.list_archived()) == 1


def test_invalid_transition_raises(tmp_queue: ReviewQueueManager, engine: RecommendationEngine, parser: GenericJobParser) -> None:
    posting = parser.parse_pasted_text(JD_TPM, job_id="tpm3", title="TPM", company="Global")
    rec = engine.recommend_from_resume(RESUME_TPM, [posting])[1][0]
    entry_id = tmp_queue.enqueue_recommendation(rec)
    tmp_queue.approve(entry_id)
    with pytest.raises(ValueError, match="Invalid transition"):
        tmp_queue.reject(entry_id, reason="too late")


def test_low_match_rejection_priority(engine: RecommendationEngine, parser: GenericJobParser) -> None:
    posting = parser.parse_pasted_text(JD_PRODUCT, job_id="low", title="PM", company="SaaS")
    rec = engine.recommend_from_resume(RESUME_TPM, [posting])[1][0]
    assert rec.recommendation_priority == RecommendationPriority.LOW_MATCH or (
        rec.recommendation_priority == RecommendationPriority.BORDERLINE and not rec.eligibility_passed
    )


def test_decision_memory_counters(tmp_memory: DecisionMemory, engine: RecommendationEngine, parser: GenericJobParser) -> None:
    tpm = engine.recommend_from_resume(RESUME_TPM, [parser.parse_pasted_text(JD_TPM, job_id="a", title="T", company="C")])[1][0]
    prod = engine.recommend_from_resume(RESUME_TPM, [parser.parse_pasted_text(JD_PRODUCT, job_id="b", title="P", company="C")])[1][0]
    tmp_memory.record_approval(tpm)
    tmp_memory.record_rejection(prod, reason="product mismatch")
    summary = tmp_memory.summary()
    assert summary["approved_count"] == 1
    assert summary["rejected_count"] == 1


def test_pipeline_end_to_end(tmp_path: Path) -> None:
    queue_dir = tmp_path / "queue"
    pipeline = RecommendationPipeline()
    pipeline._queue = ReviewQueueManager(data_dir=queue_dir)
    pipeline._memory = DecisionMemory(data_dir=queue_dir)
    pipeline._queue.initialize()
    pipeline._memory.initialize()

    out = pipeline.run(
        PipelineInput(
            resume_text=RESUME_TPM,
            jobs=[
                {"job_id": "p1", "title": "TPM", "company": "A", "jd_text": JD_TPM},
                {"job_id": "p2", "title": "PM", "company": "B", "jd_text": JD_PRODUCT},
            ],
        ),
    )
    assert len(out.results) == 2
    assert out.results[0].recommendation.overall_match >= out.results[1].recommendation.overall_match
    entry_id = out.results[0].queue_entry_id
    assert entry_id
    pipeline.approve(entry_id)
    assert len(pipeline._queue.list_approved()) == 1
