"""Deterministic candidate ↔ job matching."""

from career_intelligence_engine.matching.job_match_engine import (
    JobMatchEngine,
    match_candidate_to_job,
)
from career_intelligence_engine.matching.result import JobMatchResult

__all__ = [
    "JobMatchEngine",
    "JobMatchResult",
    "match_candidate_to_job",
]
