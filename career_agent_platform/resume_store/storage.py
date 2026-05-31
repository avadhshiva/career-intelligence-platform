"""Deterministic JSON persistence for resumes (Windows-safe paths)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable

from resume_store.models import CanonicalResume, ResumeIdentity


def _platform_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resumes_root() -> Path:
    return _platform_root() / "data" / "resumes"


def ensure_resumes_root() -> Path:
    root = resumes_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def active_resume_marker_path() -> Path:
    """Path storing the last active resume_id for restart continuity."""
    return _platform_root() / "data" / "active_resume.json"


def load_active_resume_id() -> str:
    path = active_resume_marker_path()
    if not path.exists():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    rid = str((payload or {}).get("resume_id") or "").strip()
    return rid


def save_active_resume_id(resume_id: str) -> None:
    from demo_mode import persistence_writes_enabled

    if not persistence_writes_enabled():
        return
    rid = str(resume_id or "").strip()
    if not rid:
        return
    path = active_resume_marker_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"resume_id": rid}, indent=2, sort_keys=True), encoding="utf-8")


def compute_resume_id(*, raw_text: str) -> str:
    """Stable identity for the same resume content."""
    normalized = "\n".join((raw_text or "").replace("\r\n", "\n").splitlines()).strip()
    return sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _resume_path(resume_id: str) -> Path:
    return ensure_resumes_root() / f"{resume_id}.json"


@dataclass(frozen=True)
class ResumeStore:
    """Small file-based store. No DB, no embeddings."""

    root: Path = resumes_root()

    def save(self, identity: ResumeIdentity) -> Path:
        from demo_mode import persistence_writes_enabled

        if not persistence_writes_enabled():
            return _resume_path(identity.resume_id)
        ensure_resumes_root()
        path = _resume_path(identity.resume_id)
        payload = identity.to_dict()
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def load(self, resume_id: str) -> ResumeIdentity | None:
        if not resume_id:
            return None
        path = _resume_path(resume_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return ResumeIdentity.from_dict(data)

    def list(self) -> list[ResumeIdentity]:
        root = ensure_resumes_root()
        items: list[ResumeIdentity] = []
        for p in sorted(root.glob("*.json")):
            try:
                items.append(ResumeIdentity.from_dict(json.loads(p.read_text(encoding="utf-8"))))
            except Exception:
                continue
        # newest first when uploaded_at is present
        return sorted(items, key=lambda r: r.uploaded_at or "", reverse=True)

    def upsert_many(self, identities: Iterable[ResumeIdentity]) -> None:
        for item in identities:
            self.save(item)


@dataclass(frozen=True)
class CanonicalResumeStore:
    """File-based store for the canonical resume object."""

    root: Path = resumes_root()

    def save(self, resume: CanonicalResume) -> Path:
        from demo_mode import persistence_writes_enabled

        if not persistence_writes_enabled():
            return _resume_path(resume.resume_id)
        ensure_resumes_root()
        path = _resume_path(resume.resume_id)
        payload = resume.to_dict()
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def load(self, resume_id: str) -> CanonicalResume | None:
        if not resume_id:
            return None
        path = _resume_path(resume_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        canonical = CanonicalResume.from_dict(data)
        # Auto-migrate legacy identity-only payloads to canonical structure.
        try:
            if "resume_identity" not in (data or {}) or "resume_text" not in (data or {}):
                self.save(canonical)
        except Exception:
            pass
        return canonical

    def list(self) -> list[CanonicalResume]:
        root = ensure_resumes_root()
        items: list[CanonicalResume] = []
        for p in sorted(root.glob("*.json")):
            try:
                items.append(CanonicalResume.from_dict(json.loads(p.read_text(encoding="utf-8"))))
            except Exception:
                continue
        return sorted(items, key=lambda r: r.created_at or "", reverse=True)

