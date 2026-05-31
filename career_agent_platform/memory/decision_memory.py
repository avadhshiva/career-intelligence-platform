"""Decision memory — deterministic counters from human approve/reject patterns."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from recommendation_engine import RecommendationResult


def _platform_root() -> Path:
    return Path(__file__).resolve().parents[1]


class DecisionMemory:
    """
    Tracks approved/rejected job patterns without ML.
    Uses simple frequency counters for role families, domains, and companies.
    """

    def __init__(self, data_dir: Path | None = None) -> None:
        root = data_dir or (_platform_root() / "applications" / "data")
        self._data_dir = root
        self._path = root / "decision_memory.json"

    def initialize(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text(
                json.dumps(self._empty_store(), indent=2),
                encoding="utf-8",
            )

    def _empty_store(self) -> dict[str, Any]:
        return {
            "approved_patterns": [],
            "rejected_patterns": [],
            "preferred_role_families": {},
            "preferred_domains": {},
            "preferred_companies": {},
            "rejected_role_families": {},
            "rejected_domains": {},
            "rejected_companies": {},
            "updated_at": None,
        }

    def _load(self) -> dict[str, Any]:
        self.initialize()
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def record_approval(self, rec: RecommendationResult) -> None:
        self._record(rec, approved=True)

    def record_rejection(self, rec: RecommendationResult, reason: str = "") -> None:
        self._record(rec, approved=False, reason=reason)

    def _record(
        self,
        rec: RecommendationResult,
        *,
        approved: bool,
        reason: str = "",
    ) -> None:
        store = self._load()
        pattern = self._extract_pattern(rec, reason)
        bucket = "approved_patterns" if approved else "rejected_patterns"
        store[bucket].append(pattern)

        role = pattern.get("role_family", "unknown")
        domain = pattern.get("domain", "unknown")
        company = pattern.get("company", "unknown")

        if approved:
            self._increment(store, "preferred_role_families", role)
            self._increment(store, "preferred_domains", domain)
            self._increment(store, "preferred_companies", company)
        else:
            self._increment(store, "rejected_role_families", role)
            self._increment(store, "rejected_domains", domain)
            self._increment(store, "rejected_companies", company)

        self._save(store)

    def _extract_pattern(self, rec: RecommendationResult, reason: str) -> dict[str, Any]:
        detail = rec.match_detail or {}
        role_family = detail.get("primary_role_family")
        if not role_family:
            job_profile = detail.get("job_profile") or {}
            role_family = job_profile.get("primary_role_family", "unknown")
        domain_flags = []
        if detail.get("is_product_heavy"):
            domain_flags.append("product")
        if detail.get("is_operations_heavy"):
            domain_flags.append("operations")
        if detail.get("is_ai_transformation"):
            domain_flags.append("ai_transformation")
        if detail.get("is_release_governance_heavy"):
            domain_flags.append("release_governance")
        domain = domain_flags[0] if domain_flags else rec.recommendation_priority.value

        return {
            "job_id": rec.job_id,
            "title": rec.job_title,
            "company": rec.company,
            "role_family": str(role_family),
            "domain": domain,
            "priority": rec.recommendation_priority.value,
            "overall_match": rec.overall_match,
            "rejection_reason": reason,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _increment(store: dict[str, Any], key: str, value: str) -> None:
        counters = store.setdefault(key, {})
        counters[value] = int(counters.get(value, 0)) + 1

    def top_preferred_role_families(self, n: int = 5) -> list[tuple[str, int]]:
        store = self._load()
        items = store.get("preferred_role_families") or {}
        return Counter(items).most_common(n)

    def top_rejected_role_families(self, n: int = 5) -> list[tuple[str, int]]:
        store = self._load()
        items = store.get("rejected_role_families") or {}
        return Counter(items).most_common(n)

    def summary(self) -> dict[str, Any]:
        store = self._load()
        return {
            "approved_count": len(store.get("approved_patterns") or []),
            "rejected_count": len(store.get("rejected_patterns") or []),
            "preferred_role_families": store.get("preferred_role_families") or {},
            "preferred_domains": store.get("preferred_domains") or {},
            "preferred_companies": store.get("preferred_companies") or {},
            "rejected_role_families": store.get("rejected_role_families") or {},
            "updated_at": store.get("updated_at"),
        }
