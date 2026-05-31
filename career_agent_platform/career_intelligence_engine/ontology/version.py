"""Ontology fingerprint for drift monitoring (no runtime scoring impact)."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

_ONTOLOGY_FILES = (
    "role_families.py",
    "capability_graph.py",
    "capability_vectors.py",
)


@lru_cache(maxsize=1)
def get_ontology_version() -> str:
    """Stable short hash over core ontology modules."""
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for name in _ONTOLOGY_FILES:
        path = root / name
        if path.is_file():
            digest.update(name.encode("utf-8"))
            digest.update(path.read_bytes())
    return f"ontology-{digest.hexdigest()[:12]}"
