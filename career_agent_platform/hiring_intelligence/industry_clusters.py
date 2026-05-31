"""Industry cluster mappings for market intelligence."""

from __future__ import annotations

from dataclasses import dataclass

INDUSTRY_CLUSTERS: dict[str, tuple[str, ...]] = {
    "Retail + Enterprise Tech": ("Retail", "Enterprise Technology"),
    "Financial Services": ("Financial Services",),
    "Consulting & Professional Services": ("Consulting", "Professional Services", "Technology Services"),
    "Enterprise SaaS & Platform": ("Technology", "Enterprise SaaS", "Enterprise Software"),
    "AI & Data Services": ("Technology", "AI Services", "AI SaaS", "Talent Platform"),
}


@dataclass(frozen=True)
class IndustryClusterSummary:
    cluster: str
    fit_score: float
    why_fit: list[str]
    top_companies: list[str]


def cluster_for_industries(industries: tuple[str, ...]) -> str:
    for cluster, members in INDUSTRY_CLUSTERS.items():
        if any(ind in members for ind in industries):
            return cluster
    return "Enterprise Technology"
