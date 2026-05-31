"""Tests for capability graph and deterministic capability inference."""

from __future__ import annotations

from career_intelligence_engine.intelligence.capability_inference import infer_capabilities
from career_intelligence_engine.ontology.capability_graph import (
    CAPABILITY_CLUSTERS,
    normalize_skill,
    normalize_skills,
)


def test_capability_cluster_count() -> None:
    assert 15 <= len(CAPABILITY_CLUSTERS) <= 20


def test_synonym_normalization_pmp() -> None:
    assert normalize_skill("PMP") == "program management"


def test_synonym_normalization_tpm() -> None:
    assert normalize_skill("TPM") == "technical program management"


def test_synonym_normalization_genai() -> None:
    assert normalize_skill("Gen AI") == "generative ai"


def test_normalize_skills_deduplicates() -> None:
    skills = normalize_skills(["PMP", "program management", "pmp"])
    assert skills == ["program management"]


def test_infer_capabilities_enterprise_delivery() -> None:
    skills = [
        "program management",
        "release management",
        "stakeholder management",
        "governance",
    ]
    result = infer_capabilities(skills)
    assert "enterprise_delivery" in result
    entry = result["enterprise_delivery"]
    assert entry["score"] > 0.3
    assert len(entry["evidence"]) >= 2
    assert 0.0 < entry["confidence"] <= 1.0


def test_infer_capabilities_ai_transformation() -> None:
    skills = ["generative ai", "llm", "rag", "responsible ai", "mlops"]
    result = infer_capabilities(skills)
    assert "ai_transformation" in result
    assert result["ai_transformation"]["score"] >= 0.4


def test_infer_capabilities_empty() -> None:
    assert infer_capabilities([]) == {}


def test_deterministic_repeatability() -> None:
    skills = ["program management", "azure", "agile", "erp"]
    first = infer_capabilities(skills)
    second = infer_capabilities(skills)
    assert first == second


def test_unrelated_skills_low_scores() -> None:
    skills = ["quota attainment", "recruiting", "payroll"]
    result = infer_capabilities(skills)
    delivery = result.get("enterprise_delivery", {}).get("score", 0)
    ai = result.get("ai_transformation", {}).get("score", 0)
    assert delivery < 0.35
    assert ai < 0.35
