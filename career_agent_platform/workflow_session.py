"""Cross-page workflow continuity (resume, JD context, workspace handoff)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from job_sources.job_posting import JobPosting


def store_parsed_resume(text: str) -> None:
    cleaned = (text or "").strip()
    if cleaned:
        st.session_state.parsed_resume_text = cleaned


def get_parsed_resume() -> str:
    return (st.session_state.get("parsed_resume_text") or "").strip()


def clear_parsed_resume() -> None:
    st.session_state.pop("parsed_resume_text", None)
    st.session_state.pop("resume_replace_requested", None)


def store_match_postings(postings: list[JobPosting]) -> None:
    """Persist minimal posting payloads for refine / re-score."""
    st.session_state.match_postings = [_posting_snapshot(p) for p in postings]


def get_match_postings() -> list[dict[str, Any]]:
    return list(st.session_state.get("match_postings") or [])


def capture_approval_for_workspace(*, entry_id: str, job_id: str) -> None:
    st.session_state.workspace_selected_entry_id = entry_id
    st.session_state.workspace_selected_job_id = job_id
    st.session_state.pending_workspace_generate = True


def consume_pending_workspace_generate() -> bool:
    if st.session_state.pop("pending_workspace_generate", False):
        return True
    return False


def request_resume_replace() -> None:
    st.session_state.resume_replace_requested = True


def resume_replace_requested() -> bool:
    return bool(st.session_state.get("resume_replace_requested"))


def clear_resume_replace_request() -> None:
    st.session_state.pop("resume_replace_requested", None)


def _posting_snapshot(posting: JobPosting) -> dict[str, Any]:
    from job_sources.normalization import normalize_job_posting

    norm = normalize_job_posting(posting)
    entity = norm.to_dict()
    return {
        "job_id": posting.job_id,
        "title": norm.normalized_title,
        "company": norm.company_name,
        "location": norm.location,
        "source": norm.source,
        "raw_text": posting.raw_text,
        "normalized": entity,
        "job_entity": entity,
        "clean_display_label": norm.clean_display_label,
    }


def set_active_resume_variant(variant_id: str, label: str = "") -> None:
    st.session_state.active_resume_variant_id = variant_id
    if label:
        st.session_state.active_resume_variant_label = label


def get_active_resume_variant() -> tuple[str, str]:
    return (
        str(st.session_state.get("active_resume_variant_id") or ""),
        str(st.session_state.get("active_resume_variant_label") or ""),
    )


def set_active_recommendation_job_id(job_id: str) -> None:
    st.session_state.active_recommendation_job_id = job_id


def get_active_recommendation_job_id() -> str:
    return str(st.session_state.get("active_recommendation_job_id") or "").strip()


def set_active_company(company: str) -> None:
    if company:
        st.session_state.active_company = company


def get_active_company() -> str:
    return str(st.session_state.get("active_company") or "").strip()


def set_active_package_id(package_id: str) -> None:
    st.session_state.active_package_id = package_id


def get_active_package_id() -> str:
    return str(st.session_state.get("active_package_id") or "").strip()
