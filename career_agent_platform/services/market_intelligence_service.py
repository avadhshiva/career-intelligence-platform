"""Curated market intelligence — reuses deterministic recommendation engine."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from career_intelligence_engine.models.candidate_profile import CandidateProfile
from job_sources.generic_job_parser import GenericJobParser
from job_sources.job_posting import JobPosting
from presentation.explainability import humanize_dimensions, top_n, uniq
from presentation.sanitize import sanitize_bullet_list, sanitize_display_text
from recommendation_engine import (
    RecommendationEngine,
    RecommendationPriority,
    RecommendationResult,
)
from services.listing_urls import resolve_listing_url

_PLATFORM_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FEED_PATH = _PLATFORM_ROOT / "data" / "market_feed.json"

_LOCATION_ORDER = (
    "Bengaluru",
    "Hyderabad",
    "Chennai",
    "Pune",
    "Coimbatore",
    "Remote",
)

_PRIORITY_LABEL = {
    RecommendationPriority.STRONG_MATCH: "Apply first",
    RecommendationPriority.GOOD_MATCH: "Strong candidate",
    RecommendationPriority.BORDERLINE: "Explore selectively",
    RecommendationPriority.LOW_MATCH: "Low priority",
}

_JARGON_RE = re.compile(
    r"(hard eligibility gates|capability vector similarity|overall match \d+%|job weight \d+%)",
    re.IGNORECASE,
)

_ROLE_FAMILY_REQUIREMENTS: dict[str, tuple[str, str]] = {
    "technical_program_management": (
        "Cross-functional technical delivery, release governance, and architecture alignment",
        "Stakeholder management across engineering, product, and operations",
    ),
    "program_leadership": (
        "Portfolio governance, executive steering, and benefits realization",
        "Enterprise program delivery with matrix stakeholder leadership",
    ),
    "release_governance": (
        "Release train, PI planning, SDLC governance, and deployment quality",
        "Agile-at-scale delivery with compliance-aware release management",
    ),
    "ai_transformation": (
        "Enterprise AI strategy, operating-model redesign, and adoption metrics",
        "Transformation office coordination with executive sponsorship",
    ),
    "ai_program_management": (
        "AI portfolio governance and responsible AI delivery",
        "Technical program leadership across data, platform, and business teams",
    ),
    "enterprise_delivery": (
        "Large-scale program delivery with governance and transformation coordination",
        "Consulting-style PMO delivery across business and technology stakeholders",
    ),
    "product_management": (
        "Product roadmap ownership, customer discovery, and outcome metrics",
        "Go-to-market alignment with engineering and design partners",
    ),
    "enterprise_operations": (
        "Run-state operations, SLA management, and incident reduction",
        "Service management with continuous improvement accountability",
    ),
}


@dataclass(frozen=True)
class CuratedOpportunity:
    """Normalized row from market_feed.json."""

    job_id: str
    company: str
    role: str
    location: str
    jd_summary: str
    source: str
    job_url: str
    role_family: str
    salary_range: str | None = None


@dataclass
class ScoredOpportunity:
    """Curated opportunity with deterministic fit from RecommendationEngine."""

    opportunity: CuratedOpportunity
    recommendation: RecommendationResult

    @property
    def estimated_fit(self) -> float:
        return self.recommendation.overall_match

    @property
    def priority_label(self) -> str:
        return _PRIORITY_LABEL.get(
            self.recommendation.recommendation_priority,
            "Review",
        )


@dataclass
class CompanyHiringSignal:
    company: str
    opportunity_count: int
    avg_fit: float
    top_location: str


@dataclass
class MarketIntelligenceReport:
    disclaimer: str
    feed_description: str
    top_companies: list[CompanyHiringSignal] = field(default_factory=list)
    by_location: dict[str, list[ScoredOpportunity]] = field(default_factory=dict)
    total_opportunities: int = 0


class MarketIntelligenceService:
    """Load curated feed, score with existing engine, group for UI."""

    def __init__(
        self,
        *,
        engine: RecommendationEngine | None = None,
        feed_path: Path | str | None = None,
    ) -> None:
        self._engine = engine or RecommendationEngine()
        self._parser = GenericJobParser()
        self._feed_path = Path(feed_path) if feed_path else DEFAULT_FEED_PATH

    def load_feed_records(self, path: Path | str | None = None) -> list[dict[str, Any]]:
        feed_file = Path(path) if path else self._feed_path
        payload = json.loads(feed_file.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "opportunities" in payload:
            return list(payload["opportunities"])
        if isinstance(payload, list):
            return payload
        return []

    def load_feed_meta(self, path: Path | str | None = None) -> dict[str, str]:
        feed_file = Path(path) if path else self._feed_path
        payload = json.loads(feed_file.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {
                "description": "Curated market feed",
                "disclaimer": "Curated opportunities with estimated fit.",
            }
        return {
            "description": str(payload.get("description") or "Curated market feed"),
            "disclaimer": str(
                payload.get("disclaimer") or "Curated opportunities with estimated fit.",
            ),
        }

    def normalize_opportunity(self, record: dict[str, Any]) -> CuratedOpportunity:
        company = str(record.get("company") or "").strip()
        role = str(record.get("role") or record.get("title") or "").strip()
        location = str(record.get("location") or "").strip()
        raw_url = str(record.get("job_url") or record.get("url") or "").strip()
        job_url = resolve_listing_url(
            company=company,
            role=role,
            location=location,
            job_url=raw_url,
            normalized_title=str(record.get("normalized_title") or role).strip(),
            company_name=company,
        )
        return CuratedOpportunity(
            job_id=str(record.get("job_id") or record.get("id") or ""),
            company=company,
            role=role,
            location=location,
            jd_summary=str(record.get("jd_summary") or record.get("summary") or "").strip(),
            source=str(record.get("source") or "curated_feed"),
            job_url=job_url,
            role_family=str(record.get("role_family") or "").strip(),
            salary_range=(str(record["salary_range"]).strip() if record.get("salary_range") else None),
        )

    def to_job_posting(self, opp: CuratedOpportunity) -> JobPosting:
        raw = self._compose_raw_text(opp)
        record = {
            "job_id": opp.job_id,
            "title": opp.role,
            "company": opp.company,
            "location": opp.location,
            "source": opp.source,
            "raw_text": raw,
        }
        posting = self._parser.parse_json_record(record)
        if posting.parsed_job_profile is not None:
            detail = posting.parsed_job_profile.model_dump(mode="json")
            detail["location"] = opp.location
            detail["role_family"] = opp.role_family
        return posting

    @staticmethod
    def _compose_raw_text(opp: CuratedOpportunity) -> str:
        lines = [
            opp.role,
            f"{opp.company} | {opp.location}",
            "",
            "Summary",
            opp.jd_summary,
            "",
            "Responsibilities",
        ]
        family_key = opp.role_family.strip().lower()
        req_pair = _ROLE_FAMILY_REQUIREMENTS.get(
            family_key,
            (
                "Enterprise program delivery, governance, and cross-functional leadership",
                "Stakeholder management with measurable delivery outcomes",
            ),
        )
        lines.extend(
            [
                "",
                "Requirements",
                f"• {req_pair[0]}",
                f"• {req_pair[1]}",
            ],
        )
        return "\n".join(lines)

    def score_opportunities(
        self,
        profile: CandidateProfile,
        records: list[dict[str, Any]] | None = None,
    ) -> list[ScoredOpportunity]:
        rows = records if records is not None else self.load_feed_records()
        opportunities = [self.normalize_opportunity(r) for r in rows if r.get("job_id")]
        postings = [self.to_job_posting(o) for o in opportunities]
        recommendations = self._engine.recommend(profile, postings)
        by_id = {r.job_id: r for r in recommendations}
        scored: list[ScoredOpportunity] = []
        for opp in opportunities:
            rec = by_id.get(opp.job_id)
            if rec is None:
                continue
            rec.match_detail = dict(rec.match_detail or {})
            rec.match_detail["location"] = opp.location
            rec.match_detail["job_url"] = opp.job_url
            rec.match_detail["jd_summary"] = opp.jd_summary
            rec.match_detail["role_family"] = opp.role_family
            rec.match_detail["salary_range"] = opp.salary_range
            scored.append(ScoredOpportunity(opportunity=opp, recommendation=rec))
        return sorted(
            scored,
            key=lambda s: (
                RecommendationEngine.PRIORITY_ORDER[s.recommendation.recommendation_priority],
                -s.estimated_fit,
                s.opportunity.company,
            ),
        )

    def build_report(
        self,
        profile: CandidateProfile,
        *,
        feed_path: Path | str | None = None,
    ) -> MarketIntelligenceReport:
        meta = self.load_feed_meta(feed_path)
        scored = self.score_opportunities(
            profile,
            self.load_feed_records(feed_path),
        )
        by_location: dict[str, list[ScoredOpportunity]] = {loc: [] for loc in _LOCATION_ORDER}
        for item in scored:
            loc = item.opportunity.location or "Other"
            by_location.setdefault(loc, []).append(item)
        for loc in list(by_location.keys()):
            by_location[loc].sort(
                key=lambda s: (-s.estimated_fit, s.opportunity.company),
            )
        top_companies = self._aggregate_companies(scored)
        return MarketIntelligenceReport(
            disclaimer=meta["disclaimer"],
            feed_description=meta["description"],
            top_companies=top_companies,
            by_location={k: v for k, v in by_location.items() if v},
            total_opportunities=len(scored),
        )

    @staticmethod
    def _aggregate_companies(scored: list[ScoredOpportunity]) -> list[CompanyHiringSignal]:
        buckets: dict[str, list[ScoredOpportunity]] = {}
        for item in scored:
            buckets.setdefault(item.opportunity.company, []).append(item)
        signals: list[CompanyHiringSignal] = []
        for company, items in buckets.items():
            fits = [s.estimated_fit for s in items]
            loc_counts: dict[str, int] = {}
            for s in items:
                loc_counts[s.opportunity.location] = loc_counts.get(s.opportunity.location, 0) + 1
            top_loc = max(loc_counts, key=loc_counts.get) if loc_counts else ""
            signals.append(
                CompanyHiringSignal(
                    company=company,
                    opportunity_count=len(items),
                    avg_fit=sum(fits) / len(fits) if fits else 0.0,
                    top_location=top_loc,
                ),
            )
        signals.sort(key=lambda s: (-s.avg_fit, -s.opportunity_count, s.company))
        return signals[:8]

    def concise_rationale(self, rec: RecommendationResult, *, max_items: int = 3) -> list[str]:
        """Short, non-repetitive bullets for market cards — reuses match explainability."""
        candidates: list[str] = []
        summary_tokens = (rec.recruiter_summary or "").lower()

        for item in sanitize_bullet_list(rec.top_strengths or rec.strengths)[:2]:
            line = _tone_strength(item)
            if line and line.lower()[:40] not in summary_tokens:
                candidates.append(line)

        lenses = (rec.match_detail or {}).get("fit_lenses") or {}
        for lens_text in lenses.values():
            cleaned = sanitize_display_text(str(lens_text))
            if cleaned and not _JARGON_RE.search(cleaned):
                if "gap" in cleaned.lower() or "below" in cleaned.lower():
                    candidates.append(cleaned)
                elif cleaned.lower()[:40] not in summary_tokens:
                    candidates.append(cleaned)

        for item in top_n(rec.why_matched, 3):
            cleaned = sanitize_display_text(item)
            if cleaned and not _JARGON_RE.search(cleaned):
                if cleaned.lower()[:40] not in summary_tokens:
                    candidates.append(cleaned)

        for gap in sanitize_bullet_list(rec.gaps or rec.missing_capabilities)[:1]:
            toned = _tone_gap(gap)
            if toned and toned.lower()[:40] not in summary_tokens:
                candidates.append(toned)

        if len(candidates) < max_items:
            for dim in humanize_dimensions(rec.dominant_dimensions)[:1]:
                phrase = f"Credible {dim.lower()} for this opportunity"
                if phrase.lower()[:40] not in summary_tokens:
                    candidates.append(phrase)

        return _dedupe_rationale(candidates, max_items=max_items)


def _tone_strength(text: str) -> str:
    t = text.strip().rstrip(".")
    if not t:
        return ""
    lower = t.lower()
    if lower.startswith(("strong ", "good ", "credible ", "governance ", "profile ")):
        return t[0].upper() + t[1:] if t else t
    if any(
        kw in lower
        for kw in ("align", "evidenced", "differentiator", "documented", "credible")
    ):
        return t[0].upper() + t[1:]
    return t[0].upper() + t[1:] if t else t


def _tone_gap(text: str) -> str:
    t = text.strip().rstrip(".")
    if not t:
        return ""
    lower = t.lower()
    if lower.startswith(("limited ", "gap", "strategic ", "role expects", "not yet")):
        return t[0].upper() + t[1:]
    if "less emphasized" in lower or "underrepresented" in lower or "lighter" in lower:
        return t[0].upper() + t[1:]
    return t[0].upper() + t[1:] if t else t


def _dedupe_rationale(items: list[str], *, max_items: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        line = sanitize_display_text(raw)
        if not line:
            continue
        key = line.lower()[:60]
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
        if len(out) >= max_items:
            break
    return out
