"""Hide low-quality analytics labels from user-facing dashboards."""

from __future__ import annotations

_UNKNOWN_TOKENS = frozenset(
    {
        "",
        "unknown",
        "n/a",
        "na",
        "none",
        "other",
        "unspecified",
        "company",
        "role",
    },
)


def is_low_quality_label(value: str | None) -> bool:
    return (value or "").strip().lower() in _UNKNOWN_TOKENS


def filter_role_families(
    items: list[tuple[str, int]],
) -> list[tuple[str, int]]:
    return [(label, count) for label, count in items if not is_low_quality_label(label)]


def filter_company_scores(
    items: list[tuple[str, float]],
) -> list[tuple[str, float]]:
    return [(company, score) for company, score in items if not is_low_quality_label(company)]


def filter_aging_buckets(buckets: dict[str, int]) -> dict[str, int]:
    return {k: v for k, v in buckets.items() if not is_low_quality_label(k) and v > 0}
