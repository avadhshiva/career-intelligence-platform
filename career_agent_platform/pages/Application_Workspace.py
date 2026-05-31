"""Phase 5C/5D — Application package workspace with lifecycle state machine."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from application_tracking.tracker import ApplicationTracker

from application_workspace.export import package_as_plaintext

from application_workspace.models import ApplicationApprovalState

from application_workspace.package_builder import ApplicationPackageBuilder

from application_workspace.review_manager import ApplicationReviewManager

from application_workspace.state_machine import allowed_targets

from presentation.actions import render_lifecycle_actions

from presentation.hero import render_workspace_hero

from presentation.labels import safe_company, safe_title

from presentation.demo_banner import render_demo_mode_banner
from presentation.journey import render_next_step, render_page_intro
from presentation.nav import render_primary_nav

from presentation.sanitize import (
    humanize_gap_line,
    sanitize_artifact_prose,
    sanitize_bullet_list,
    sanitize_display_text,
    sanitize_gap_question,
)

from presentation.explainability import humanize_dimensions, uniq

from review_queue_manager import ReviewQueueManager
from state_hygiene import get_valid_queue_entries, get_valid_packages, safe_cleanup_demo_state
from job_sources.normalization import NormalizedJobPosting, pretty_job_label
from presentation.job_card import render_workspace_job_context
from resume_routing.router import routing_from_recommendation
from resume_store.session_manager import get_active_resume
from resume_store.storage import load_active_resume_id
from workflow_session import (
    clear_resume_replace_request,
    consume_pending_workspace_generate,
    request_resume_replace,
    resume_replace_requested,
    set_active_company,
    set_active_package_id,
    set_active_recommendation_job_id,
    set_active_resume_variant,
)

_PLATFORM_ROOT = Path(__file__).resolve().parents[1]

_EXPORT_ROOT = _PLATFORM_ROOT / "applications" / "data" / "application_packages" / "exports"

_STATE_BADGE = {

    ApplicationApprovalState.GENERATED: ":blue[generated]",

    ApplicationApprovalState.UNDER_REVIEW: ":orange[under review]",

    ApplicationApprovalState.APPROVED: ":green[approved]",

    ApplicationApprovalState.REJECTED: ":red[rejected]",

    ApplicationApprovalState.EXPORTED: ":violet[exported]",

    ApplicationApprovalState.ARCHIVED: ":gray[archived]",

    ApplicationApprovalState.REOPENED: ":orange[reopened]",

}

def _init_session() -> None:

    if "app_review_mgr" not in st.session_state:

        st.session_state.app_review_mgr = ApplicationReviewManager()

        st.session_state.app_review_mgr.initialize()

    if "app_package_builder" not in st.session_state:

        st.session_state.app_package_builder = ApplicationPackageBuilder(

            st.session_state.app_review_mgr,

        )

    if "app_tracker" not in st.session_state:

        st.session_state.app_tracker = ApplicationTracker()

        st.session_state.app_tracker.initialize()

    if "queue_mgr_ws" not in st.session_state:

        st.session_state.queue_mgr_ws = ReviewQueueManager()

        st.session_state.queue_mgr_ws.initialize()

    if "demo_state_cleaned" not in st.session_state:
        safe_cleanup_demo_state()
        st.session_state.demo_state_cleaned = True

    if "demo_queue_purged_ws" not in st.session_state:

        st.session_state.queue_mgr_ws.purge_demo_entries()

        st.session_state.demo_queue_purged_ws = True

    if "selected_package_id" not in st.session_state:

        st.session_state.selected_package_id = None

def _handle_transition(result) -> None:

    if result.success:

        st.success(result.user_message)

    else:

        st.warning(result.user_message)

def _render_timeline(pkg) -> None:

    if not pkg.state_history:

        st.caption("No transition history yet.")

        return

    for entry in reversed(pkg.state_history[-12:]):

        icon = "OK" if entry.success else "BLOCKED"

        st.text(

            f"[{icon}] {entry.timestamp[:19]}  "

            f"{entry.from_state} -> {entry.to_state}  "

            f"({entry.reviewer_action_reason})",

        )

        if entry.review_notes:

            st.caption(f"  notes: {entry.review_notes}")

        if entry.warning:

            st.caption(f"  warning: {entry.warning}")

def _render_package_inputs(

    queue: ReviewQueueManager,

    builder: ApplicationPackageBuilder,

    review_mgr: ApplicationReviewManager,

    *,

    heading: str = "Generate or switch package",

) -> None:

    st.subheader(heading)

    st.caption(
        "Pick an approved role and generate your package. "
        "Resume text carries over from recommendations when available.",
    )

    qv = get_valid_queue_entries(queue)
    approved = qv.approved

    if not approved:
        from presentation.journey import render_empty_state

        render_empty_state(
            title="No approved roles yet",
            body="Application packages are created from roles you approve on Recommendations.",
            steps=[
                "On **Recommendations**, generate ranked matches and open each card.",
                "Click **Approve** on roles you want to pursue (aim for at least two in a demo).",
                "Return here and select an approved job to generate your package.",
            ],
            primary_page="pages/Job_Recommendations.py",
            primary_label="Go to Recommendations",
        )
        return

    labels = []
    for e in approved:
        rec = e.get("recommendation") or {}
        labels.append(
            pretty_job_label(
                title=rec.get("job_title"),
                company=rec.get("company"),
                location=(rec.get("match_detail") or {}).get("location"),
                normalized=(rec.get("match_detail") or {}).get("normalized"),
            ),
        )
    default_index = 0
    selected_job_id = st.session_state.get("workspace_selected_job_id")
    if selected_job_id:
        for idx, entry_row in enumerate(approved):
            if entry_row.get("job_id") == selected_job_id:
                default_index = idx
                break

    if not labels:
        st.info("No approved packages yet")
        return

    choice = st.selectbox("Approved job", labels, index=default_index)

    entry = approved[labels.index(choice)]

    if not str(st.session_state.get("active_resume_id") or "").strip():
        st.session_state.active_resume_id = load_active_resume_id()

    active = get_active_resume(st.session_state)
    resume_text = (active.resume.resume_text if active.resume else "").strip()
    show_override = resume_replace_requested()

    if active.resume:
        with st.container():
            st.markdown("**Active resume**")
            c1, c2, c3 = st.columns(3)
            c1.metric("File", active.resume.file_name or "Resume")
            c2.metric(
                "Role family",
                str((active.resume.resume_identity or {}).get("role_family") or "").replace("_", " ").title(),
            )
            years = (active.resume.resume_identity or {}).get("experience_years")
            exp = f"{float(years):.0f}y" if isinstance(years, (int, float)) and years else "—"
            c3.metric("Experience", exp)
            skills = (active.resume.resume_identity or {}).get("top_skills") or []
            if skills:
                st.caption("Top skills: " + ", ".join(list(skills)[:6]))
            label = (active.resume.resume_identity or {}).get("recommended_resume_label") or ""
            if label:
                st.caption(f"Profile label: {label}")

    if show_override:
        resume_text = st.text_area(
            "Override resume text",
            value=resume_text,
            height=160,
            help="Only use when you need to replace the saved resume for this package.",
        )
        if resume_text.strip():
            clear_resume_replace_request()
        if st.button("Use saved resume instead", key="ws_use_saved_resume"):
            clear_resume_replace_request()
            st.rerun()
    elif not resume_text:
        st.warning(
            "Upload a resume on **Recommendations** first — packages use your saved resume automatically.",
        )
    else:
        if st.button("Override resume", key="ws_replace_resume"):
            request_resume_replace()
            st.rerun()

    from recommendation_engine import RecommendationResult

    rec = RecommendationResult.from_dict(entry["recommendation"])
    route = routing_from_recommendation(rec)
    if route:
        st.info(f"**Routed resume:** {route.recommended_resume}")
        for line in route.why_selected[:2]:
            st.caption(f"• {line}")
        set_active_resume_variant(route.variant_id, route.recommended_resume)
    set_active_recommendation_job_id(rec.job_id)
    set_active_company(rec.company)
    entry_id = entry.get("entry_id", "")
    autobuild_key = f"autobuild_{entry_id or rec.job_id}"

    if (
        consume_pending_workspace_generate()
        and resume_text.strip()
        and not st.session_state.get(autobuild_key)
    ):
        pkg = builder.build(rec, resume_text.strip())
        st.session_state.selected_package_id = pkg.package_id
        set_active_package_id(pkg.package_id)
        st.session_state[autobuild_key] = True
        st.success("Application package generated from your approved role.")
        st.rerun()

    if st.button("Generate application package", type="primary"):

        if not resume_text.strip():

            st.error("Resume text is required. Approve a role on Recommendations first, or replace resume above.")

        else:

            pkg = builder.build(rec, resume_text.strip())

            st.session_state.selected_package_id = pkg.package_id
            set_active_package_id(pkg.package_id)

            st.session_state[autobuild_key] = True

            st.success("Application package generated.")

            st.rerun()

    existing_pkgs = get_valid_packages(review_mgr)
    if existing_pkgs:
        st.markdown("**Saved packages**")
        pkg_labels = [f"{safe_title(p.job_title)} @ {safe_company(p.company)}" for p in existing_pkgs]
        pick = st.selectbox("Switch to saved package", pkg_labels)
        sel_idx = pkg_labels.index(pick)
        st.session_state.selected_package_id = existing_pkgs[sel_idx].package_id
        st.rerun()
    else:
        st.caption("No saved packages yet")

def _render_artifact_tabs(pkg) -> None:

    tab_resume, tab_cover, tab_rec, tab_prep, tab_quality = st.tabs(

        ["Tailored resume", "Cover letter", "Recruiter messages", "Interview prep", "Quality"],

    )

    with tab_resume:

        body = sanitize_artifact_prose(
            pkg.tailored_resume_text,
            job_title=pkg.job_title,
            company=pkg.company,
        )

        if body:

            st.text_area("Tailored resume", body, height=300, disabled=True)

        else:

            st.caption("Tailored resume not available yet.")

    with tab_cover:

        if pkg.cover_letter:

            letter = sanitize_artifact_prose(
                pkg.cover_letter.body,
                job_title=pkg.job_title,
                company=pkg.company,
            )

            if letter:

                st.text_area("Cover letter", letter, height=300, disabled=True)

            else:

                st.caption("Cover letter content is empty.")

        else:

            st.caption("Cover letter not generated.")

    with tab_rec:

        if pkg.recruiter_message:

            linkedin = sanitize_artifact_prose(
                pkg.recruiter_message.linkedin_intro,
                job_title=pkg.job_title,
                company=pkg.company,
            )
            hm = sanitize_artifact_prose(
                pkg.recruiter_message.hiring_manager_note,
                job_title=pkg.job_title,
                company=pkg.company,
            )
            referral = sanitize_artifact_prose(
                pkg.recruiter_message.referral_request,
                job_title=pkg.job_title,
                company=pkg.company,
            )

            if linkedin:

                st.markdown("**LinkedIn**")

                st.write(linkedin)

            if hm:

                st.markdown("**Hiring manager**")

                st.write(hm)

            if referral:

                st.markdown("**Referral**")

                st.write(referral)

            if not any((linkedin, hm, referral)):

                st.caption("Recruiter messages will appear after package generation.")

        else:

            st.caption("Recruiter messages not generated.")

    with tab_prep:

        if pkg.interview_prep:

            focus = sanitize_bullet_list(pkg.interview_prep.likely_focus_areas)

            if focus:

                st.write("**Focus areas:**", ", ".join(focus))

            questions = [

                q

                for q in (

                    sanitize_gap_question(item)

                    for item in pkg.interview_prep.probable_gap_questions

                )

                if q

            ]

            for q in questions:

                st.write(f"- {q}")

            if not focus and not questions:

                st.caption("Interview prep summary is being assembled.")

        else:

            st.caption("Interview prep not generated.")

    with tab_quality:

        if pkg.quality_scores:

            q = pkg.quality_scores

            from presentation.sanitize import format_score_percent

            q1, q2, q3, q4 = st.columns(4)

            q1.metric("Overall", format_score_percent(q.overall_application_quality_score))

            q2.metric("Resume alignment", format_score_percent(q.resume_alignment))

            q3.metric("ATS readiness", format_score_percent(q.ats_readiness))

            q4.metric("Leadership fit", format_score_percent(q.leadership_fit))

        else:

            st.caption("Quality scores not available.")

render_primary_nav(active="Application workspace")

render_demo_mode_banner()

st.title("Application workspace")
render_page_intro(
    active="workspace",
    purpose=(
        "Build and review application packages for approved roles: tailored resume, cover letter, "
        "recruiter messages, and interview prep. Resume text carries over from Recommendations."
    ),
)

_init_session()

review_mgr: ApplicationReviewManager = st.session_state.app_review_mgr

builder: ApplicationPackageBuilder = st.session_state.app_package_builder

tracker: ApplicationTracker = st.session_state.app_tracker

queue: ReviewQueueManager = st.session_state.queue_mgr_ws

package_id = st.session_state.get("selected_package_id")

if package_id:

    pkg = review_mgr.get_package(package_id)

    state_badge = _STATE_BADGE.get(pkg.approval_status, pkg.approval_status.value)

    allowed = allowed_targets(pkg.approval_status)

    snap = pkg.recommendation_snapshot or {}

    job_label = pretty_job_label(
        title=pkg.job_title,
        company=pkg.company,
        normalized=(pkg.recommendation_snapshot or {}).get("normalized"),
    )

    st.info(f"**Current package:** {job_label}")

    with st.expander("Switch role or regenerate package", expanded=False):

        _render_package_inputs(

            queue,

            builder,

            review_mgr,

            heading="New package from approved role",

        )

    if pkg.last_warning:

        st.warning(pkg.last_warning)

    snap_entity = snap.get("job_entity") or snap.get("normalized")
    route_snap = (snap.get("resume_routing") or {}).get("recommended_resume", "")
    if snap_entity:
        render_workspace_job_context(NormalizedJobPosting.from_dict(snap_entity), recommended_resume=route_snap)
        st.caption(f"Lifecycle {state_badge}")
    else:
        render_workspace_hero(pkg, state_badge=state_badge)

    with st.expander("Details (explainability & quality)", expanded=False):

        for line in sanitize_bullet_list(pkg.explanation):

            st.write(f"- {line}")

        dom = humanize_dimensions(snap.get("dominant_dimensions") or [])

        miss = humanize_dimensions(snap.get("missing_dimensions") or [])

        c1, c2 = st.columns(2)

        with c1:

            st.markdown("**Dominant dimensions**")

            st.write(", ".join(dom) if dom else "—")

        with c2:

            st.markdown("**Missing dimensions**")

            st.write(", ".join(miss) if miss else "—")

        risks = sanitize_bullet_list(

            (pkg.interview_prep.risk_areas if pkg.interview_prep else []),

        )

        if risks:

            st.markdown("**Risk areas**")

            for r in risks:

                st.write(f"- {humanize_gap_line(r) or r}")

    with st.expander("Transition history", expanded=False):

        _render_timeline(pkg)

    _render_artifact_tabs(pkg)

    st.divider()

    st.subheader("Next step")

    def _on_export_paths(paths: dict) -> None:

        st.success("Exported:")

        for fmt, p in paths.items():

            st.code(f"{fmt}: {p}")

    render_lifecycle_actions(

        pkg,

        package_id,

        allowed,

        review_mgr,

        _EXPORT_ROOT,

        on_transition=_handle_transition,

        on_export_paths=_on_export_paths,

    )

    with st.expander("Package utilities", expanded=False):

        tracked = tracker.get_by_package(package_id)

        if tracked:

            st.caption(f"Tracker: **{tracked.status.value}** · last action {tracked.last_action_at[:19]}")

            new_status = st.selectbox(

                "Update tracker status",

                ["applied", "recruiter_contacted", "interviewing", "offer", "rejected", "withdrawn"],

                key=f"tracker_{package_id}",

            )

            util_notes = st.text_input("Tracker notes (optional)", key=f"tracker_notes_{package_id}")

            if st.button("Save tracker status", key=f"save_tracker_{package_id}"):

                from application_tracking.models import ApplicationStatus

                tracker.update_status(

                    tracked.application_id,

                    ApplicationStatus(new_status),

                    notes=util_notes,

                )

                st.success(f"Tracker updated to {new_status}")

                st.rerun()

        else:

            st.caption("Tracker record syncs when package is saved.")

        st.download_button(

            "Download plaintext bundle",

            package_as_plaintext(pkg),

            file_name=f"{pkg.source_job_id}_application_package.txt",

        )

else:
    _render_package_inputs(queue, builder, review_mgr, heading="Start here")

if package_id:
    st.divider()
    render_next_step(
        message="Review strategic alignment and pipeline health across all packages.",
        page_path="pages/Application_Dashboard.py",
        button_label="Career cockpit",
    )

