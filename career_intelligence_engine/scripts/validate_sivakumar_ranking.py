"""Print eligibility + ranking validation for Sivakumar-style resume."""

from __future__ import annotations

from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.intelligence.executive_signals import detect_executive_signals
from career_intelligence_engine.scoring.career_distance import CareerDistanceScorer
from career_intelligence_engine.tests.fixtures.calibration_resumes import RESUME_SIVAKUMAR_STYLE


def main() -> None:
    engine = CareerIdentityEngine()
    profile = engine.analyze_text(RESUME_SIVAKUMAR_STYLE)
    matrix = profile.explanations["eligibility_matrix"]
    excluded = profile.explanations["excluded_from_ranking"]
    ranked = CareerDistanceScorer().rank_role_families(profile)

    print("=== GATE VALUES ===")
    print("product_ownership_depth:", profile.explanations.get("product_ownership_depth"))
    print("operational_run_depth:", profile.explanations.get("operational_run_depth"))
    print("product_thinking (raw):", profile.capability_raw_scores.get("product_thinking"))
    print(
        "operational_management (raw):",
        profile.capability_raw_scores.get("operational_management"),
    )

    print("\n=== INELIGIBLE FAMILIES ===")
    for fid in excluded:
        print(f"  {fid}: {matrix[fid].get('exclusion_reason')}")

    print("\n=== PRIMARY / ADJACENT ===")
    print("primary:", profile.primary_career_track.value)
    print("adjacent:", [a.value for a in profile.adjacent_role_families])

    print("\n=== TOP 10 RANKED (after two-stage) ===")
    for i, (fid, result) in enumerate(ranked[:10], 1):
        row = next(
            x for x in profile.explanations["score_trace"] if x["role_family"] == fid.value
        )
        print(f"{i}. {fid.value}")
        print(
            f"   ontology={row['ontology_score']} vector={row['vector_score']} "
            f"final={row['final_score']}"
        )
        print(
            f"   elig: primary={row['eligible_for_primary']} "
            f"adj={row['eligible_for_adjacency']} rank={row['eligible_for_ranking']}"
        )
        print(f"   proximity={result.proximity}")

    parsed = engine._parser.parse_text(RESUME_SIVAKUMAR_STYLE)
    skill = engine._skills.extract(parsed.raw_text, parsed.bullets)
    ont = engine._score_role_families(parsed, skill, detect_executive_signals(parsed))
    before_ont = sorted(ont.items(), key=lambda x: -x[1])[:10]
    print("\n=== BEFORE (ontology global sort — delivery language dominates) ===")
    for i, (fid, score) in enumerate(before_ont, 1):
        print(f"{i}. {fid.value}: ontology={score:.2f}")


if __name__ == "__main__":
    main()
