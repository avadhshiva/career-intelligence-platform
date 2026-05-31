"""Release metadata for ops logs and public repo presentation (no runtime behavior impact)."""

from __future__ import annotations

__version__ = "0.5.1-release-candidate"
__release_label__ = "release-candidate"

# Deterministic engine: no random seeds in matching; scores derive from ontology + fixtures.
DETERMINISM_NOTE = (
    "Matching and ranking are deterministic for a given resume + JD input. "
    "No LLM calls in the default recommendation path."
)

BUILD_INFO = {
    "version": __version__,
    "release": __release_label__,
    "deterministic": True,
    "benchmark_status": "4 known adjacency/ranking test failures — see docs/benchmark_drift_notes.md",
    "evaluation_layer": "snapshot/diff utilities in career_agent_platform/evaluation/",
    "planned_version": "0.6.0-evaluation-layer",
}
