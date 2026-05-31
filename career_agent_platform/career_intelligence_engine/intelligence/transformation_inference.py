"""Transformation and AI maturity inference (calibrated, evidence-based)."""

from __future__ import annotations

from dataclasses import dataclass

from career_intelligence_engine.intelligence.evidence_calibration import (
    analyze_evidence_depth,
    calibrated_transformation_focus,
    infer_ai_maturity,
)
from career_intelligence_engine.models.ontology import AIMaturity, ParsedResume


@dataclass
class TransformationResult:
    transformation_focus: float
    ai_maturity: AIMaturity
    signals: list[str]


class TransformationInference:
    def infer(self, parsed: ParsedResume) -> TransformationResult:
        depth = analyze_evidence_depth(parsed)
        signals = list(depth.signals)

        transformation_focus = calibrated_transformation_focus(depth)
        ai_maturity = infer_ai_maturity(depth)

        if depth.transform_generic_hits:
            signals.append(f"transformation_mentions:{depth.transform_generic_hits}")
        if depth.ai_strategy_hits:
            signals.append(f"ai_strategy_mentions:{depth.ai_strategy_hits}")
        if depth.ai_governance_hits:
            signals.append(f"ai_governance_mentions:{depth.ai_governance_hits}")
        if ai_maturity != AIMaturity.NONE:
            signals.append(f"ai_maturity:{ai_maturity.value}")

        return TransformationResult(
            transformation_focus=transformation_focus,
            ai_maturity=ai_maturity,
            signals=signals,
        )
