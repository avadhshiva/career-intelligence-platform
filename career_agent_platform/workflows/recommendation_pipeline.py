"""Recommendation pipeline — end-to-end workflow using the embedded engine.



Resume identity → job ingestion → deterministic recommendations → human review queue.

Does not invoke browser automation or auto-apply.

"""



from __future__ import annotations



from dataclasses import dataclass, field

from typing import Any



from job_sources.generic_job_parser import GenericJobParser

from job_sources.job_posting import JobPosting

from memory.decision_memory import DecisionMemory

from recommendation_engine import RecommendationEngine, RecommendationResult

from review_queue_manager import ReviewQueueManager





@dataclass

class PipelineInput:

    resume_text: str

    jobs: list[dict[str, str]]  # keys: job_id, title, company, jd_text, optional source/location





@dataclass

class PipelineJobResult:

    job_id: str

    posting: JobPosting

    recommendation: RecommendationResult

    queue_entry_id: str | None = None





@dataclass

class PipelineOutput:

    career_identity: Any

    results: list[PipelineJobResult] = field(default_factory=list)





class RecommendationPipeline:

    """Orchestrates ingestion, deterministic matching, ranking, and human review gating."""



    def __init__(self) -> None:

        self._engine = RecommendationEngine()

        self._parser = GenericJobParser()

        self._queue = ReviewQueueManager()

        self._memory = DecisionMemory()



    def run(

        self,

        pipeline_input: PipelineInput,

        auto_enqueue_review: bool = True,

    ) -> PipelineOutput:

        postings: list[JobPosting] = []

        for job in pipeline_input.jobs:

            postings.append(

                self._parser.parse_pasted_text(

                    job["jd_text"],

                    job_id=job["job_id"],

                    title=job.get("title", ""),

                    company=job.get("company", ""),

                    location=job.get("location", ""),

                ),

            )



        profile, recommendations = self._engine.recommend_from_resume(

            pipeline_input.resume_text,

            postings,

        )

        results: list[PipelineJobResult] = []

        entry_ids: list[str] = []

        if auto_enqueue_review:

            self._queue.initialize()

            entry_ids = self._queue.enqueue_many(recommendations)



        posting_by_id = {p.job_id: p for p in postings}

        for rec, entry_id in zip(recommendations, entry_ids or [None] * len(recommendations)):

            results.append(

                PipelineJobResult(

                    job_id=rec.job_id,

                    posting=posting_by_id[rec.job_id],

                    recommendation=rec,

                    queue_entry_id=entry_id,

                ),

            )



        return PipelineOutput(career_identity=profile, results=results)



    def approve(self, entry_id: str, notes: str = "") -> None:

        entry = self._queue.approve(entry_id, notes=notes)

        rec = RecommendationResult.from_dict(entry["recommendation"])

        self._memory.record_approval(rec)



    def reject(self, entry_id: str, reason: str = "", notes: str = "") -> None:

        entry = self._queue.reject(entry_id, reason=reason, notes=notes)

        rec = RecommendationResult.from_dict(entry["recommendation"])

        self._memory.record_rejection(rec, reason=reason)


