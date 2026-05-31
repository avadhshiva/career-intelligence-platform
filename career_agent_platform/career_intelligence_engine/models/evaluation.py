"""Evaluation and benchmarking datatypes (deterministic, no ML)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class ConfidenceResult:
    confidence_score: float
    confidence_level: str
    ambiguity_score: float
    evidence_density: float
    top_gap: float
    confidence_contributors: tuple[str, ...] = ()
    confidence_penalties: tuple[str, ...] = ()
    dominance_margin: float = 0.0
    ambiguity_level: str = "HIGH"
    ranking_stability: float = 0.0
    score_margin_confidence: float = 0.0
    evidence_density_confidence: float = 0.0
    contamination_risk: float = 0.0
    ambiguity_penalty: float = 0.0
    calibration_strength: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence_score": round(self.confidence_score, 4),
            "confidence_level": self.confidence_level,
            "ambiguity_score": round(self.ambiguity_score, 4),
            "evidence_density": round(self.evidence_density, 4),
            "top_gap": round(self.top_gap, 4),
            "confidence_contributors": list(self.confidence_contributors),
            "confidence_penalties": list(self.confidence_penalties),
            "dominance_margin": round(self.dominance_margin, 4),
            "ambiguity_level": self.ambiguity_level,
            "ranking_stability": round(self.ranking_stability, 4),
            "score_margin_confidence": round(self.score_margin_confidence, 4),
            "evidence_density_confidence": round(self.evidence_density_confidence, 4),
            "contamination_risk": round(self.contamination_risk, 4),
            "ambiguity_penalty": round(self.ambiguity_penalty, 4),
            "calibration_strength": round(self.calibration_strength, 4),
        }


@dataclass
class ContaminationSignal:
    family: str
    contamination_score: float
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "contamination_score": round(self.contamination_score, 4),
            "reasons": list(self.reasons),
        }
