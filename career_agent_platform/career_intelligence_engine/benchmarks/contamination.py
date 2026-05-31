"""Ontology contamination heuristics for benchmark evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from career_intelligence_engine.models.ontology import RoleFamilyId

# (source_fixture_id, contaminant_family, human-readable cause)
CONTAMINATION_RULES: tuple[tuple[str, RoleFamilyId, str], ...] = (
    (
        "technical_program_manager_enterprise",
        RoleFamilyId.PRODUCT_DELIVERY,
        "TPM delivery language inflating Product Delivery",
    ),
    (
        "program_leadership_enterprise",
        RoleFamilyId.OPERATIONS,
        "Program Leadership portfolio language inflating Operations",
    ),
    (
        "ai_transformation_director",
        RoleFamilyId.AI_GOVERNANCE,
        "AI Transformation strategy language inflating AI Governance",
    ),
    (
        "enterprise_architect",
        RoleFamilyId.SOFTWARE_ENGINEERING,
        "Architecture coordination inflating Software Engineering",
    ),
)

# Minimum score ratio (contaminant / primary) that triggers a warning
CONTAMINATION_SCORE_RATIO_THRESHOLD = 0.72
CONTAMINATION_TOP_N_RANK = 5


@dataclass(frozen=True)
class ContaminationFinding:
    fixture_id: str
    source_family: RoleFamilyId
    contaminant_family: RoleFamilyId
    cause: str
    primary_score: float
    contaminant_score: float
    contaminant_rank: int

    @property
    def score_ratio(self) -> float:
        if self.primary_score <= 0:
            return 0.0
        return self.contaminant_score / self.primary_score

    @property
    def is_contaminated(self) -> bool:
        return (
            self.contaminant_rank <= CONTAMINATION_TOP_N_RANK
            and self.score_ratio >= CONTAMINATION_SCORE_RATIO_THRESHOLD
        )


def detect_contamination(
    fixture_id: str,
    primary: RoleFamilyId,
    ranked_scores: list[tuple[RoleFamilyId, float]],
) -> list[ContaminationFinding]:
    """Flag known cross-family inflation patterns for a benchmark fixture."""
    score_by_family = {fid: score for fid, score in ranked_scores}
    rank_by_family = {fid: i + 1 for i, (fid, _) in enumerate(ranked_scores)}
    primary_score = score_by_family.get(primary, 0.0)
    findings: list[ContaminationFinding] = []

    for rule_fixture, contaminant, cause in CONTAMINATION_RULES:
        if rule_fixture != fixture_id:
            continue
        contaminant_score = score_by_family.get(contaminant, 0.0)
        findings.append(
            ContaminationFinding(
                fixture_id=fixture_id,
                source_family=primary,
                contaminant_family=contaminant,
                cause=cause,
                primary_score=primary_score,
                contaminant_score=contaminant_score,
                contaminant_rank=rank_by_family.get(contaminant, 99),
            )
        )
    return findings
