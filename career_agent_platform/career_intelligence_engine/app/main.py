"""FastAPI service for career identity and job matching (Phase 2)."""

from __future__ import annotations

import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.matching.job_match_engine import JobMatchEngine
from career_intelligence_engine.matching.result import JobMatchResult
from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.job_profile import JobProfile
from career_intelligence_engine.models.ontology import RoleFamilyId
from career_intelligence_engine.scoring.career_distance import CareerDistanceScorer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Career Intelligence Engine",
    description="Phase 2: Resume career identity and deterministic job matching.",
    version="0.2.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_engine = CareerIdentityEngine()
_scorer = CareerDistanceScorer()
_match_engine = JobMatchEngine()


class AnalyzeTextRequest(BaseModel):
    resume_text: str = Field(..., min_length=50)


class AnalyzeJobTextRequest(BaseModel):
    job_text: str = Field(..., min_length=30)


class MatchRequest(BaseModel):
    profile: CandidateProfile
    job_text: str = Field(..., min_length=30)


class RoleProximityItem(BaseModel):
    role_family: str
    display_name: str
    distance: float
    proximity: float
    semantic_distance: float | None = None
    dominant_dimensions: list[str] = Field(default_factory=list)
    weak_dimensions: list[str] = Field(default_factory=list)
    missing_dimensions: list[str] = Field(default_factory=list)
    vector_explanation: str = ""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "phase": "2"}


@app.post("/analyze", response_model=CandidateProfile)
async def analyze_resume(file: UploadFile = File(...)) -> CandidateProfile:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    try:
        profile = _engine.analyze_bytes(content, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Analyze failed")
        raise HTTPException(status_code=500, detail="Analysis failed") from exc
    return profile


@app.post("/analyze/text", response_model=CandidateProfile)
def analyze_text(body: AnalyzeTextRequest) -> CandidateProfile:
    return _engine.analyze_text(body.resume_text)


@app.post("/analyze/role-proximity")
def role_proximity(profile: CandidateProfile) -> dict[str, list[RoleProximityItem]]:
    """Rank role families by career proximity (for explainability / future matching)."""
    ranked = _scorer.rank_role_families(profile)
    from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES

    items = [
        RoleProximityItem(
            role_family=fid.value,
            display_name=ROLE_FAMILIES[fid].display_name,
            distance=result.distance,
            proximity=result.proximity,
            semantic_distance=getattr(result, "semantic_distance", None) or result.distance,
            dominant_dimensions=getattr(result, "dominant_dimensions", []) or [],
            weak_dimensions=getattr(result, "weak_dimensions", []) or [],
            missing_dimensions=getattr(result, "missing_dimensions", []) or [],
            vector_explanation=getattr(result, "vector_explanation", None) or "",
        )
        for fid, result in ranked
    ]
    return {"rankings": items}


@app.post("/analyze/job", response_model=JobProfile)
def analyze_job(body: AnalyzeJobTextRequest) -> JobProfile:
    """Parse a job description into a structured JobProfile."""
    return _match_engine.parse_job(body.job_text)


@app.post("/match")
def match_candidate_job(body: MatchRequest) -> dict[str, object]:
    """Deterministic candidate ↔ job match with explainability."""
    result: JobMatchResult = _match_engine.match(body.profile, body.job_text)
    job = _match_engine.parse_job(body.job_text)
    return {
        "job": job.model_dump(mode="json"),
        "match": result.to_dict(),
    }
