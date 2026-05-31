"""Deterministic capability inference from normalized resume skills."""

from __future__ import annotations

from career_intelligence_engine.ontology.capability_graph import (
    CAPABILITY_CLUSTERS,
    _normalize_key,
    cluster_for_term,
    normalize_skills,
)


def _skill_matches_term(skill: str, term: str) -> bool:
    """True when normalized skill equals or contains the cluster term."""
    skill_key = _normalize_key(skill)
    term_key = _normalize_key(term)
    if not skill_key or not term_key:
        return False
    if skill_key == term_key:
        return True
    if len(term_key) >= 4 and term_key in skill_key:
        return True
    if len(skill_key) >= 4 and skill_key in term_key:
        return True
    return False


def infer_capabilities(normalized_skills: list[str]) -> dict[str, dict]:
    """
    Map resume skills into enterprise capability clusters.

    Returns a dict keyed by cluster id with score, evidence, and confidence.
    Scoring is purely deterministic: matched terms / cluster size, capped at 1.0.
    """
    skills = normalize_skills(normalized_skills)
    if not skills:
        return {}

    results: dict[str, dict] = {}

    for cluster_id, terms in CAPABILITY_CLUSTERS.items():
        evidence: list[str] = []
        match_weight = 0.0

        for skill in skills:
            direct_cluster = cluster_for_term(skill)
            if direct_cluster == cluster_id:
                evidence.append(skill)
                match_weight += 1.0
                continue
            for term in terms:
                if _skill_matches_term(skill, term):
                    if term not in evidence:
                        evidence.append(term)
                    match_weight += 1.0
                    break

        if match_weight <= 0:
            continue

        cluster_size = max(len(terms), 1)
        raw_score = match_weight / cluster_size
        score = round(min(1.0, raw_score), 2)
        confidence = round(min(1.0, len(evidence) / max(3, cluster_size * 0.35)), 2)

        results[cluster_id] = {
            "score": score,
            "evidence": sorted(set(evidence)),
            "confidence": confidence,
        }

    return results
