"""Score drift detection against frozen benchmark baselines."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DRIFT_THRESHOLD_RATIO = 0.15

_BASELINE_PATH = Path(__file__).resolve().parent / "baseline_scores.json"


@dataclass(frozen=True)
class DriftWarning:
    fixture_id: str
    family: str
    metric: str
    baseline: float
    current: float
    delta_ratio: float

    @property
    def message(self) -> str:
        pct = self.delta_ratio * 100
        return (
            f"{self.fixture_id}/{self.family} {self.metric}: "
            f"baseline={self.baseline:.4f} current={self.current:.4f} "
            f"drift={pct:+.1f}%"
        )


def load_baseline(path: Path | None = None) -> dict[str, dict[str, dict[str, float]]]:
    """Load fixture_id -> family -> {ontology_score, final_score}."""
    p = path or _BASELINE_PATH
    if not p.exists():
        return {}
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def save_baseline(
    snapshot: dict[str, dict[str, dict[str, float]]],
    path: Path | None = None,
) -> Path:
    p = path or _BASELINE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, sort_keys=True)
    return p


def detect_drift(
    fixture_id: str,
    current_scores: dict[str, dict[str, float]],
    baseline: dict[str, dict[str, dict[str, float]]] | None = None,
    threshold: float = DRIFT_THRESHOLD_RATIO,
) -> list[DriftWarning]:
    """Compare current per-family scores to baseline; warn if change exceeds threshold."""
    base = (baseline or load_baseline()).get(fixture_id, {})
    warnings: list[DriftWarning] = []
    for family, metrics in current_scores.items():
        base_metrics = base.get(family, {})
        for metric in ("ontology_score", "final_score"):
            if metric not in metrics or metric not in base_metrics:
                continue
            cur = float(metrics[metric])
            prev = float(base_metrics[metric])
            if prev <= 0 and cur <= 0:
                continue
            denom = max(abs(prev), 1e-6)
            delta_ratio = abs(cur - prev) / denom
            if delta_ratio > threshold:
                warnings.append(
                    DriftWarning(
                        fixture_id=fixture_id,
                        family=family,
                        metric=metric,
                        baseline=prev,
                        current=cur,
                        delta_ratio=delta_ratio,
                    )
                )
    return warnings
