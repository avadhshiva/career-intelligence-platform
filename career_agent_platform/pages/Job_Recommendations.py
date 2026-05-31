"""Phase 5A — Job recommendations with human review queue."""



from __future__ import annotations

import logging

from pathlib import Path



import streamlit as st

logger = logging.getLogger(__name__)



from career_intelligence_engine.models.candidate_profile import CandidateProfile

from job_sources.generic_job_parser import GenericJobParser

from job_sources.ingest import ingest_file, ingest_pasted

from memory.decision_memory import DecisionMemory

from presentation.actions import render_recommendation_actions

from presentation.hero import render_recommendation_details, render_recommendation_hero

from presentation.labels import match_category_badge, safe_company, safe_title
from job_sources.normalization import pretty_job_label
from intelligence_enrichment import enrich_recommendations

from presentation.demo_banner import render_demo_mode_banner
from presentation.governance import render_governance_panel
from presentation.ingestion_workflow import (
    build_workflow_snapshot,
    render_engine_room_header,
    render_pipeline_rail,
    render_workflow_status_line,
)
from presentation.journey import render_next_step, render_page_intro
from presentation.nav import render_primary_nav

from presentation.market import render_market_intelligence_tab

from recommendation_engine import ApprovalStatus, RecommendationEngine, RecommendationResult

from services.market_intelligence_service import MarketIntelligenceService

from resume_extraction import extract_resume_from_upload
from resume_store.session_manager import (
    build_canonical_resume,
    get_active_resume,
    persist_and_activate_canonical_resume,
)
from resume_store.storage import CanonicalResumeStore, load_active_resume_id

from monitoring.ops_log import log_event, timed_operation
from monitoring.reliability_signals import log_recommendation_run_signals
from review_queue_manager import ReviewQueueManager
from state_hygiene import get_valid_queue_entries
from workflow_session import (
    get_match_postings,
    get_parsed_resume,
    store_match_postings,
    store_parsed_resume,
)



_PLATFORM_ROOT = Path(__file__).resolve().parents[1]

_SAMPLE_FEED = _PLATFORM_ROOT / "data" / "sample_job_feed.json"





def _load_preview_recommendations(

    engine: RecommendationEngine,

    queue: ReviewQueueManager,

) -> None:

    """Optional `?preview=hero` loads deterministic sample recs for UI review."""

    if st.query_params.get("preview") != "hero":

        return

    if st.session_state.get("recommendations"):

        return

    if not _SAMPLE_FEED.exists():

        return

    from career_intelligence_engine.tests.fixtures.calibration_resumes import RESUME_TPM



    postings = GenericJobParser().parse_json_file(_SAMPLE_FEED)

    profile, recs = engine.recommend_from_resume(RESUME_TPM, postings)

    st.session_state.career_profile = profile
    st.session_state.recommendations = recs

    st.session_state.entry_map = {}


def _sync_recommendations_from_queue(
    recs: list[RecommendationResult],
    queue: ReviewQueueManager,
) -> None:
    """Merge queue decisions into session cards so hero + queue stay aligned."""
    if not recs:
        return

    qv = get_valid_queue_entries(queue)
    all_entries = qv.pending + qv.approved + qv.rejected
    by_job = {
        e["job_id"]: e
        for e in ReviewQueueManager.unique_entries_by_job(all_entries)
        if e and isinstance(e, dict) and e.get("job_id")
    }

    # Rebuild the mapping from the current queue snapshot so we never keep orphaned entry_ids.
    entry_map: dict[str, str] = {}
    for rec in recs:
        entry = by_job.get(rec.job_id)
        if not entry or not isinstance(entry, dict):
            continue
        if entry:
            entry_map[rec.job_id] = entry["entry_id"]
        payload = entry.get("recommendation") or {}
        raw_status = payload.get("approval_status")
        if raw_status:
            try:
                rec.approval_status = ApprovalStatus(str(raw_status))
            except ValueError:
                pass
        reason = entry.get("rejection_reason") or payload.get("rejection_reason")
        if reason:
            rec.rejection_reason = str(reason)

    st.session_state.entry_map = entry_map


def _init_session() -> None:

    if "rec_engine" not in st.session_state:

        st.session_state.rec_engine = RecommendationEngine()

    if "queue_mgr" not in st.session_state:

        st.session_state.queue_mgr = ReviewQueueManager()

        st.session_state.queue_mgr.initialize()

    if "demo_state_cleaned" not in st.session_state:
        from state_hygiene import safe_cleanup_demo_state

        safe_cleanup_demo_state()
        st.session_state.demo_state_cleaned = True

    if "decision_memory" not in st.session_state:

        st.session_state.decision_memory = DecisionMemory()

        st.session_state.decision_memory.initialize()

    if "recommendations" not in st.session_state:

        st.session_state.recommendations: list[RecommendationResult] = []

    if "entry_map" not in st.session_state:

        st.session_state.entry_map: dict[str, str] = {}

    if "demo_queue_purged" not in st.session_state:

        removed = st.session_state.queue_mgr.purge_demo_entries()

        st.session_state.demo_queue_purged = True

        if removed:

            st.session_state.recommendations = []

            st.session_state.entry_map = {}

    # If we already have persisted queue decisions but a fresh Streamlit session,
    # reconstruct the cards from the queue snapshot so restart flows remain usable.
    if not st.session_state.get("recommendations"):
        qv = get_valid_queue_entries(st.session_state.queue_mgr)
        all_entries = qv.pending + qv.approved + qv.rejected
        restored: list[RecommendationResult] = []
        entry_map: dict[str, str] = {}
        for entry in ReviewQueueManager.unique_entries_by_job(all_entries):
            if not entry or not isinstance(entry, dict):
                continue
            rec_payload = entry.get("recommendation") or {}
            if not isinstance(rec_payload, dict) or not rec_payload:
                continue
            try:
                rec_obj = RecommendationResult.from_dict(rec_payload)
            except Exception:
                continue
            restored.append(rec_obj)
            if entry.get("entry_id") and entry.get("job_id"):
                entry_map[str(entry["job_id"])] = str(entry["entry_id"])
        if restored:
            st.session_state.recommendations = restored
            st.session_state.entry_map = entry_map
        log_event(
            "queue_restore",
            restored_count=len(restored),
            entry_count=len(all_entries),
            pending=len(qv.pending),
            approved=len(qv.approved),
            rejected=len(qv.rejected),
        )

    if "market_intel" not in st.session_state:

        st.session_state.market_intel = MarketIntelligenceService(
            engine=st.session_state.rec_engine,
        )

    # Resume identity continuity across app restarts (file-backed marker).
    if "active_resume_id" not in st.session_state:
        st.session_state.active_resume_id = load_active_resume_id()

    # Restore career profile from canonical resume on fresh restarts (cache only).
    if st.session_state.get("career_profile") is None:
        rid = str(st.session_state.get("active_resume_id") or "").strip()
        if rid:
            canonical = CanonicalResumeStore().load(rid)
            if canonical and canonical.parsed_profile:
                try:
                    st.session_state.career_profile = CandidateProfile.model_validate(canonical.parsed_profile)
                    log_event("profile_restore", source="canonical_disk", resume_id=rid)
                except Exception as exc:
                    log_event(
                        "profile_restore_failed",
                        source="canonical_disk",
                        resume_id=rid,
                        error_type=type(exc).__name__,
                    )
        else:
            log_event("profile_restore", source="none", reason="no_active_resume_id")
    else:
        log_event("profile_restore", source="session")





render_primary_nav(active="Recommendations")

render_demo_mode_banner()

st.title("Recommendations")
render_page_intro(
    active="recommendations",
    purpose=(
        "Engine room: ingest resume and job descriptions, run deterministic matching, review "
        "explainable briefs, approve roles, then hand off to Application workspace."
    ),
)



_init_session()

engine: RecommendationEngine = st.session_state.rec_engine

queue: ReviewQueueManager = st.session_state.queue_mgr

memory: DecisionMemory = st.session_state.decision_memory

_load_preview_recommendations(engine, queue)

recs: list[RecommendationResult] = st.session_state.get("recommendations") or []
_sync_recommendations_from_queue(recs, queue)



def _render_active_resume_snapshot() -> None:
    rid = str(st.session_state.get("active_resume_id") or "").strip()
    if not rid:
        return
    resume = CanonicalResumeStore().load(rid)
    if resume is None:
        return
    with st.expander("Active resume identity", expanded=False):
        c1, c2, c3 = st.columns(3)
        ident = resume.resume_identity or {}
        c1.metric("Resume", resume.file_name or "Resume")
        c2.metric("Role family", str(ident.get("role_family") or "").replace("_", " ").title() or "—")
        years = ident.get("experience_years")
        exp = f"{float(years):.0f}y" if isinstance(years, (int, float)) and years else "—"
        c3.metric("Experience", exp)
        skills = ident.get("top_skills") or []
        if skills:
            st.caption("Top skills: " + ", ".join(list(skills)[:8]))


_render_active_resume_snapshot()




def _render_getting_started() -> None:
    from presentation.journey import render_empty_state

    render_empty_state(
        title="No ranked matches yet",
        body="Add your resume and at least one job description (or the sample feed) to generate recommendations.",
        steps=[
            "Upload or paste your resume in step 1.",
            "Add job descriptions or enable the sample feed in step 2.",
            "Click **Generate ranked recommendations**, then open each card and **Approve** strong fits.",
        ],
    )





def _postings_from_snapshots(snapshots: list[dict]) -> list:
    parser = GenericJobParser()
    postings = []
    for snap in snapshots:
        raw = (snap.get("raw_text") or "").strip()
        if not raw:
            continue
        postings.append(
            parser.parse_pasted_text(
                raw,
                job_id=str(snap.get("job_id") or ""),
                title=str(snap.get("title") or "Role"),
                company=str(snap.get("company") or "Company"),
            ),
        )
    return postings


def _run_recommendation_generation(effective_resume: str, postings: list) -> None:
    if not effective_resume.strip():
        st.error("Resume text is required.")
        return
    if not postings:
        st.error("Add at least one job description.")
        return
    with timed_operation(
        "recommendation_generation",
        posting_count=len(postings),
        resume_chars=len(effective_resume.strip()),
    ):
        profile, new_recs = engine.recommend_from_resume(effective_resume, postings)
    active_label = None
    try:
        rid = str(st.session_state.get("active_resume_id") or "").strip()
        if rid:
            resume = CanonicalResumeStore().load(rid)
            if resume:
                active_label = (resume.resume_identity or {}).get("recommended_resume_label")
    except Exception:
        pass
    new_recs = enrich_recommendations(
        profile,
        new_recs,
        postings,
        active_resume_label=active_label,
    )
    st.session_state.career_profile = profile
    st.session_state.recommendations = new_recs
    store_match_postings(postings)

    # Persist canonical resume across pages/sessions (no scoring impact).
    try:
        canonical = build_canonical_resume(
            file_name=str(st.session_state.get("last_resume_filename") or "uploaded_resume"),
            resume_text=effective_resume,
            profile=profile,
        )
        persist_and_activate_canonical_resume(
            session_state=st.session_state,
            store=CanonicalResumeStore(),
            resume=canonical,
        )
    except Exception as exc:
        # Never block recommendation generation due to persistence errors.
        logger.exception(
            "Canonical resume persistence failed (parsed_profile not saved): %s",
            exc,
        )
        st.warning(
            "Recommendations were generated, but your career profile could not be saved "
            f"for Market Opportunities and Career Cockpit after restart. ({exc})"
        )

    entry_ids = queue.enqueue_many(new_recs, origin="user")
    st.session_state.entry_map = {rec.job_id: eid for rec, eid in zip(new_recs, entry_ids)}
    log_event(
        "recommendation_generation_complete",
        result_count=len(new_recs),
        queue_entries=len(entry_ids),
    )
    try:
        log_recommendation_run_signals(
            new_recs,
            resume_text=effective_resume,
            profile_primary_track=getattr(profile.primary_career_track, "value", str(profile.primary_career_track)),
            posting_count=len(postings),
        )
    except Exception:
        logger.exception("Reliability signal logging failed (non-blocking)")
    st.success(f"Generated {len(new_recs)} ranked recommendations.")
    st.rerun()


def _render_refine_analysis() -> None:
    st.caption("Adjust inputs without repeating onboarding. Ranked matches stay visible below.")
    action = st.radio(
        "Refine",
        ["Replace resume", "Replace JD", "Add another JD", "Re-run scoring"],
        horizontal=True,
        label_visibility="collapsed",
    )
    if action == "Replace resume":
        resume_file = st.file_uploader("Upload replacement resume", type=["txt", "pdf", "docx"], key="refine_resume_file")
        resume_text = st.text_area("Or paste replacement resume", height=120, key="refine_resume_paste")
        if st.button("Save resume", key="refine_save_resume"):
            effective = resume_text
            if resume_file is not None:
                upload_result = extract_resume_from_upload(resume_file.name, resume_file.getvalue())
                if upload_result.success:
                    effective = upload_result.resume_text
                elif not resume_text.strip():
                    st.error(upload_result.error or "Resume extraction failed.")
                    return
            if not (effective or "").strip():
                st.error("Provide resume text or a file.")
            else:
                store_parsed_resume(effective)
                st.success("Resume updated. Use **Re-run scoring** to refresh rankings.")
                st.rerun()
        return

    if action in ("Replace JD", "Add another JD"):
        job_source = st.selectbox("JD source", ["generic", "linkedin", "naukri", "mock"], key="refine_jd_source")
        jd_paste = st.text_area("Paste JD", height=100, key="refine_jd_paste")
        jd_files = st.file_uploader(
            "Upload JD (txt or json)",
            type=["txt", "json"],
            accept_multiple_files=True,
            key="refine_jd_files",
        )
        if st.button("Apply JD change", key="refine_apply_jd"):
            new_postings: list = []
            if jd_paste.strip():
                new_postings.append(ingest_pasted(job_source, jd_paste))
            for uploaded in jd_files or []:
                import tempfile

                suffix = Path(uploaded.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded.getvalue())
                    tmp_path = tmp.name
                new_postings.extend(ingest_file(tmp_path, source=job_source))
            if not new_postings:
                st.error("Paste or upload a job description.")
                return
            if action == "Replace JD":
                store_match_postings(new_postings)
            else:
                existing = _postings_from_snapshots(get_match_postings())
                store_match_postings(existing + new_postings)
            st.success("Job descriptions updated. Use **Re-run scoring** to refresh rankings.")
            st.rerun()
        return

    active = get_active_resume(st.session_state).resume
    resume = (active.resume_text if active else "").strip()
    snapshots = get_match_postings()
    if not resume:
        st.warning("No saved resume in this session. Replace resume first.")
        return
    if not snapshots:
        st.warning("No saved job descriptions. Replace or add a JD first.")
        return
    st.caption(f"Re-scoring with saved resume and {len(snapshots)} job description(s).")
    if st.button("Re-run scoring", type="primary", key="refine_rerun"):
        postings = _postings_from_snapshots(snapshots)
        _run_recommendation_generation(resume, postings)


def _saved_resume_text() -> str:
    active = get_active_resume(st.session_state).resume
    if active and (active.resume_text or "").strip():
        return active.resume_text.strip()
    parsed = get_parsed_resume()
    if parsed:
        return parsed
    rid = str(st.session_state.get("active_resume_id") or "").strip()
    if rid:
        canonical = CanonicalResumeStore().load(rid)
        if canonical and (canonical.resume_text or "").strip():
            return canonical.resume_text.strip()
    return ""


def _render_match_inputs(*, compact: bool = False, has_existing_matches: bool = False) -> None:
    col_resume, col_jobs = st.columns(2)

    saved_resume = _saved_resume_text()
    saved_jds = get_match_postings()

    with col_resume:
        st.subheader("1. Resume")
        if saved_resume and compact:
            st.info(
                "Session resume on file — upload or paste below to replace, "
                "or regenerate with the saved resume."
            )
        resume_file = st.file_uploader(
            "Upload resume",
            type=["txt", "pdf", "docx"],
            key="match_resume_upload",
        )
        resume_text_paste = st.text_area(
            "Or paste resume text",
            height=120 if compact else 200,
            key="match_resume_paste",
            placeholder="Paste plain-text resume here if not uploading a file.",
        )
        if resume_file is not None:
            extraction = extract_resume_from_upload(resume_file.name, resume_file.getvalue())
            if extraction.success:
                st.success("Resume parsed successfully")
                st.session_state.last_resume_filename = resume_file.name
            else:
                st.error(extraction.error or "Resume extraction failed.")

    with col_jobs:
        st.subheader("2. Job descriptions")
        if saved_jds and compact:
            st.info(
                f"{len(saved_jds)} job description(s) in session — add uploads/paste below, "
                "enable sample feed, or regenerate with saved JDs only."
            )
        job_source = st.selectbox(
            "Source",
            ["generic", "linkedin", "naukri", "mock"],
            key="match_jd_source",
        )
        jd_files = st.file_uploader(
            "Upload JD files (txt or json)",
            type=["txt", "json"],
            accept_multiple_files=True,
            key="match_jd_files",
        )
        jd_paste = st.text_area(
            "Or paste a single JD",
            height=90 if compact else 120,
            key="match_jd_paste",
        )
        use_sample = st.checkbox(
            "Load sample job feed (TPM, release, product, ops)",
            key="match_use_sample",
        )

    gen_label = (
        "Regenerate ranked recommendations"
        if has_existing_matches
        else "Generate ranked recommendations"
    )
    if st.button(gen_label, type="primary", key="match_generate_btn"):
        effective_resume = resume_text_paste.strip()
        if resume_file is not None:
            upload_result = extract_resume_from_upload(resume_file.name, resume_file.getvalue())
            if upload_result.success:
                effective_resume = upload_result.resume_text
            elif not effective_resume:
                st.error(upload_result.error or "Resume extraction failed.")
                effective_resume = ""
        if not effective_resume and saved_resume:
            effective_resume = saved_resume

        if not effective_resume.strip():
            st.error("Upload a resume file, paste resume text, or keep your saved session resume.")
        else:
            postings: list = []
            parser = GenericJobParser()
            if use_sample and _SAMPLE_FEED.exists():
                postings.extend(parser.parse_json_file(_SAMPLE_FEED))
            if jd_paste.strip():
                postings.append(ingest_pasted(job_source, jd_paste))
            for uploaded in jd_files or []:
                import tempfile

                suffix = Path(uploaded.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded.getvalue())
                    tmp_path = tmp.name
                postings.extend(ingest_file(tmp_path, source=job_source))
            if not postings and saved_jds:
                postings = _postings_from_snapshots(saved_jds)
            if not postings:
                st.error("Add at least one job description, enable the sample feed, or use saved JDs.")
            else:
                store_parsed_resume(effective_resume)
                _run_recommendation_generation(effective_resume, postings)





def _render_ranked_recommendations() -> None:

    st.markdown(
        f"**{len(recs)} roles ranked** — strongest matches open first. "
        "Scan the brief and strengths/gaps, then approve."
    )

    for rec in recs:

        entry_id = st.session_state.entry_map.get(rec.job_id, "")

        badge = match_category_badge(getattr(rec.recommendation_priority, "value", None))

        card_label = pretty_job_label(
            title=rec.job_title,
            company=rec.company,
            location=(rec.match_detail or {}).get("location"),
            normalized=(rec.match_detail or {}).get("normalized"),
        )

        with st.expander(

            f"{card_label} · {badge.label}",

            expanded=rec.recommendation_priority.value in ("STRONG_MATCH", "GOOD_MATCH"),

        ):

            render_recommendation_hero(rec)

            render_recommendation_details(rec)

            st.divider()

            render_recommendation_actions(rec, entry_id, queue, memory)





def _queue_line(entry: dict) -> str:

    rec = entry.get("recommendation") or {}

    label = pretty_job_label(
        title=rec.get("job_title"),
        company=rec.get("company"),
        location=(rec.get("match_detail") or {}).get("location"),
        normalized=(rec.get("match_detail") or {}).get("normalized"),
    )

    if label.endswith(" @ Company") or label == "Role":
        return ""

    return f"- {label}"





def _render_review_queue_body() -> None:

    tab_pending, tab_approved, tab_rejected, tab_memory = st.tabs(

        ["Pending", "Approved", "Rejected", "Decision memory"],

    )



    with tab_pending:

        qv = get_valid_queue_entries(queue)
        pending = qv.pending

        st.caption(f"{len(pending)} pending")

        for entry in pending[:20]:

            line = _queue_line(entry)

            if line:

                st.write(line)



    with tab_approved:

        qv = get_valid_queue_entries(queue)
        approved = qv.approved

        st.caption(f"{len(approved)} approved")

        for entry in approved[:20]:

            line = _queue_line(entry)

            if line:

                st.write(line)



    with tab_rejected:

        qv = get_valid_queue_entries(queue)
        rejected = qv.rejected

        st.caption(f"{len(rejected)} rejected")

        for entry in rejected[:20]:

            rec = entry.get("recommendation") or {}

            title = safe_title(rec.get("job_title"))

            reason = entry.get("rejection_reason") or rec.get("rejection_reason") or "No reason recorded"

            st.write(f"- {title}: {reason}")



    with tab_memory:

        with st.expander("Decision memory (advanced)", expanded=False):

            st.json(memory.summary())





def _render_review_queue(*, minimized: bool) -> None:

    qv = get_valid_queue_entries(queue)
    pending, approved, rejected = qv.pending, qv.approved, qv.rejected

    summary = f"{len(pending)} pending · {len(approved)} approved · {len(rejected)} rejected"




    if minimized:

        with st.expander(f"Review queue — {summary}", expanded=False):

            st.caption("Queue status for roles you've already generated. Decisions happen on each card above.")

            _render_review_queue_body()

    else:

        st.subheader("Review queue")

        st.caption(summary)

        _render_review_queue_body()





profile = st.session_state.get("career_profile")
market_service: MarketIntelligenceService = st.session_state.market_intel


def _render_matches_and_queue(*, workflow_snap) -> None:
    render_engine_room_header(snap=workflow_snap)
    _render_match_inputs(
        compact=workflow_snap.match_count > 0,
        has_existing_matches=workflow_snap.match_count > 0,
    )
    if workflow_snap.match_count > 0:
        with st.expander("Quick refine (replace one input without scrolling)", expanded=False):
            _render_refine_analysis()

    st.divider()

    if recs:
        _render_ranked_recommendations()
        st.divider()
        _render_review_queue(minimized=True)
    else:
        _render_getting_started()
        st.divider()
        _render_review_queue(minimized=False)


def _render_market_tab() -> None:
    if profile is None:
        from presentation.journey import render_empty_state

        render_empty_state(
            title="Curated market feed requires a profile",
            body="Generate ranked matches on the **Ranked matches** tab first. This feed estimates fit using the same resume analysis.",
            steps=[
                "Complete resume + job description inputs below the ranked list (or on this page before matches).",
                "Click **Generate ranked recommendations**.",
                "Return to this tab for company signals and curated opportunities.",
            ],
        )
        return
    render_market_intelligence_tab(profile=profile, service=market_service)


qv_main = get_valid_queue_entries(queue)
workflow_snap = build_workflow_snapshot(
    recommendations=recs,
    approved_count=len(qv_main.approved),
)

render_pipeline_rail(workflow_snap)
render_workflow_status_line(workflow_snap)

tab_matches, tab_market = st.tabs(["Ranked matches", "Market Intelligence"])

with tab_matches:
    _render_matches_and_queue(workflow_snap=workflow_snap)

with tab_market:
    _render_market_tab()

qv_footer = get_valid_queue_entries(queue)
if recs and len(qv_footer.approved) >= 1:
    st.divider()
    render_next_step(
        message="Explore market alignment for your profile, or build a package for an approved role.",
        page_path="pages/Market_Opportunities.py",
        button_label="Market opportunities",
    )
elif recs:
    st.caption("Approve at least one role to unlock Application workspace and the full demo path.")

if recs:
    effective_resume = ""
    try:
        rid = str(st.session_state.get("active_resume_id") or "").strip()
        if rid:
            canonical = CanonicalResumeStore().load(rid)
            if canonical:
                effective_resume = canonical.resume_text or ""
    except Exception:
        pass
    profile = st.session_state.get("career_profile")
    track = ""
    if profile is not None:
        track = getattr(profile.primary_career_track, "value", str(profile.primary_career_track))
    render_governance_panel(recs, resume_text=effective_resume, profile_primary_track=track)


