"""Job matching interfaces — implemented in Phase 2."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from career_intelligence_engine.intelligence.job_parser import parse_job_description
from career_intelligence_engine.matching.job_match_engine import (
    JobMatchEngine,
    match_candidate_to_job,
)
from career_intelligence_engine.matching.result import JobMatchResult
from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.job_profile import JobProfile


@dataclass(frozen=True)
class ParsedJobDescription:
    """Legacy alias — use JobProfile from job_parser.parse_job_description."""

    raw_text: str
    title: str | None = None
    required_skills: tuple[str, ...] = ()
    role_family_hint: str | None = None


@dataclass(frozen=True)
class MatchScore:
    """Legacy match score — prefer JobMatchResult."""

    candidate_id: str
    job_id: str
    proximity: float
    gap_summary: dict[str, Any]


class JobDescriptionParser(ABC):
    """Parse job descriptions into structured JobProfile."""

    @abstractmethod
    def parse(self, text: str) -> JobProfile:
        ...


class JobDescriptionParserImpl(JobDescriptionParser):
    def parse(self, text: str) -> JobProfile:
        return parse_job_description(text)


class CandidateJobMatcher(ABC):
    """Score candidate against a parsed JD."""

    @abstractmethod
    def match(
        self,
        profile: CandidateProfile,
        job: JobProfile,
    ) -> JobMatchResult:
        ...


class CandidateJobMatcherImpl(CandidateJobMatcher):
    def __init__(self) -> None:
        self._engine = JobMatchEngine()

    def match(
        self,
        profile: CandidateProfile,
        job: JobProfile,
    ) -> JobMatchResult:
        return match_candidate_to_job(profile, job)


class ATSScorer(ABC):
    """Future: ATS-style deterministic scoring."""

    @abstractmethod
    def score(
        self,
        profile: CandidateProfile,
        job: ParsedJobDescription,
    ) -> dict[str, float]:
        ...


class CareerTransitionAdvisor(ABC):
    """Future: recommend career transitions from profile + target."""

    @abstractmethod
    def recommend_transitions(
        self,
        profile: CandidateProfile,
        target_families: tuple[str, ...] = (),
    ) -> list[dict[str, Any]]:
        ...
