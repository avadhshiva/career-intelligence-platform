"""Streamlit UI — upload resume, view career identity."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

# Ensure package root is importable when run via `streamlit run`
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from career_intelligence_engine.app.visualizations import (
    render_capability_overlap_radar,
    render_capability_radar,
    render_confidence_analysis,
    render_contamination_warnings,
    render_dimension_lists,
    render_eligibility_matrix,
    render_gap_analysis,
    render_job_match_summary,
    render_ranking_breakdown,
    render_score_breakdown,
)
from career_intelligence_engine.intelligence.career_identity import CareerIdentityEngine
from career_intelligence_engine.intelligence.role_family_scoring import SCORER_PATH
from career_intelligence_engine.matching.job_match_engine import JobMatchEngine
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES
from career_intelligence_engine.scoring.career_distance import CareerDistanceScorer

st.set_page_config(
    page_title="Career Intelligence Engine",
    page_icon="📋",
    layout="wide",
)

st.title("Career Intelligence Engine")
st.caption(
    "Phase 2 — Resume career identity + deterministic job matching. "
    "No embedding APIs; calibrated ontology scoring."
)

engine = CareerIdentityEngine()
scorer = CareerDistanceScorer()

uploaded = st.file_uploader(
    "Upload resume",
    type=["pdf", "docx", "txt"],
    help="Supported formats: PDF, DOCX, plain text",
)

sample = st.checkbox("Use sample resume (Senior Program Manager / AI transformation)")

SAMPLE_RESUME = """
Alex Morgan
alex.morgan@email.com | Seattle, WA

SUMMARY
Senior program leader driving enterprise AI transformation and large-scale delivery
across global matrix organizations.

EXPERIENCE
Senior Program Manager | Contoso Global | Jan 2019 – Present
• Led enterprise AI transformation portfolio with 12+ cross-functional workstreams
• Partnered with C-suite executive sponsors on operating model and governance design
• Delivered multi-region platform rollout across NA, EMEA, and APAC (Fortune 500 client)
• Established program governance, steering committee, and benefits realization framework
• Managed dependency management across engineering, data science, and compliance teams

Technical Program Manager | Northwind Systems | Mar 2014 – Dec 2018
• Owned release train and SDLC alignment for cloud migration program
• Coordinated architecture reviews and CI/CD adoption across 6 product teams

Program Manager | Fabrikam Consulting | Jun 2010 – Feb 2014
• Client delivery lead for CRM and ERP implementations
• Change management and stakeholder management across regulated industries

SKILLS
Program management, PMP, agile at scale, stakeholder management, AI strategy,
GenAI, MLOps, responsible AI, SAP, Salesforce, AWS, governance, SOX, GDPR
"""

if uploaded is not None:
    content = uploaded.read()
    filename = uploaded.name
    with st.spinner("Analyzing career identity…"):
        profile = engine.analyze_bytes(content, filename)
elif sample:
    with st.spinner("Analyzing sample resume…"):
        profile = engine.analyze_text(SAMPLE_RESUME)
else:
    st.info("Upload a resume or enable the sample to begin.")
    st.stop()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Career identity")
    st.metric("Primary career track", ROLE_FAMILIES[profile.primary_career_track].display_name)
    if profile.confidence_result:
        st.metric("Confidence", profile.confidence_result.confidence_level)
    st.metric("Seniority", profile.current_seniority.value.replace("_", " ").title())
    st.metric("Leadership", profile.leadership_level.value.replace("_", " ").title())
    st.metric("Years experience", profile.years_experience or "—")
    st.metric("Transformation focus", f"{profile.transformation_focus:.0%}")
    st.metric("AI maturity", profile.ai_maturity.value.replace("_", " ").title())
    st.metric("Enterprise exposure", profile.enterprise_experience.value.replace("_", " ").title())

    st.write("**Primary domains**")
    st.write(", ".join(profile.primary_domains) or "—")
    st.write("**Secondary domains**")
    st.write(", ".join(profile.secondary_domains) or "—")

    st.write("**Adjacent role families**")
    if profile.adjacent_role_families:
        for adj in profile.adjacent_role_families:
            st.write(f"• {ROLE_FAMILIES[adj].display_name}")
    else:
        st.write("—")

    st.write("**Likely company archetypes**")
    st.write(
        ", ".join(a.value.replace("_", " ").title() for a in profile.likely_target_company_archetypes)
        or "—"
    )

with col2:
    st.subheader("Role family proximity")
    ranked = scorer.rank_role_families(profile)
    if not ranked:
        st.info("No role-family proximity results generated.")
    else:
        proximity_data = [
            {
                "Role family": ROLE_FAMILIES[fid].display_name,
                "Proximity": result.proximity,
                "Distance": getattr(result, "semantic_distance", None) or result.distance,
                "Dominant": ", ".join(getattr(result, "dominant_dimensions", [])[:3]) or "—",
                "Missing": ", ".join(getattr(result, "missing_dimensions", [])[:3]) or "—",
            }
            for fid, result in ranked[:8]
        ]
        st.dataframe(proximity_data, use_container_width=True, hide_index=True)

        explanations = [
            (fid, result)
            for fid, result in ranked[:5]
            if getattr(result, "vector_explanation", None)
        ]
        if explanations:
            with st.expander("Vector proximity explanations", expanded=False):
                for fid, result in explanations:
                    st.markdown(
                        f"**{ROLE_FAMILIES[fid].display_name}** — "
                        f"{getattr(result, 'vector_explanation', '')}"
                    )

st.subheader("Capability Profile")
render_capability_radar(profile)
render_dimension_lists(profile)

st.subheader("Ranking Breakdown")
render_ranking_breakdown(profile)
render_score_breakdown(profile)

st.subheader("Eligibility Exclusions")
render_eligibility_matrix(profile)
excluded = profile.explanations.get("excluded_from_ranking") or []
if excluded:
    st.write("**Excluded from ranking:**", ", ".join(excluded))
else:
    st.write("No families excluded from ranking.")

st.subheader("Confidence Analysis")
render_confidence_analysis(profile)

st.subheader("Contamination Diagnostics")
render_contamination_warnings(profile)

st.subheader("Gap Analysis (primary track)")
render_gap_analysis(profile)

with st.expander("Explainability — inference signals", expanded=False):
    st.json(profile.explanations)

score_trace = profile.explanations.get("score_trace") or []
scorer_path = profile.explanations.get("scorer_path") or (
    (profile.explanations.get("canonical_ranking") or {}).get("scorer_path")
) or SCORER_PATH
with st.expander("Score Trace", expanded=False):
    st.caption(f"Scorer path: `{scorer_path}`")
    if score_trace:
        trace_rows = [
            {
                "Role family": row.get("display_name", row.get("role_family")),
                "Base": row.get("base_score"),
                "Calibrated identity": row.get("calibrated_identity_score"),
                "Vector (cosine)": row.get("vector_score"),
                "Penalties": "; ".join(row.get("penalties") or []) or "—",
                "Final proximity": row.get("final_score"),
                "Confidence": row.get("confidence_level", "—"),
                "Primary eligible": row.get("eligible_for_primary", row.get("primary_track_eligible")),
                "Adjacency eligible": row.get("eligible_for_adjacency", row.get("adjacency_eligible")),
                "Ranking eligible": row.get("eligible_for_ranking"),
                "Primary": row.get("is_primary"),
                "Adjacent": row.get("is_adjacent"),
                "Filtered": row.get("filtered"),
                "Filter reason": row.get("filter_reason") or row.get("adjacency_ineligible_reason") or "—",
            }
            for row in sorted(
                score_trace,
                key=lambda r: -(r.get("final_score") or 0),
            )
        ]
        st.dataframe(trace_rows, use_container_width=True, hide_index=True)
        with st.expander("Score trace (raw JSON)", expanded=False):
            st.json(score_trace)
    else:
        st.info("No score trace available. Re-analyze the resume to generate trace data.")

st.divider()
st.subheader("Job match — candidate vs JD")
st.caption("Upload or paste a job description to compare against the analyzed resume.")

match_engine = JobMatchEngine()

jd_uploaded = st.file_uploader(
    "Upload job description",
    type=["txt"],
    key="jd_upload",
    help="Plain text JD for Phase 2 matching",
)

SAMPLE_JD_TPM = """
Senior Technical Program Manager
Contoso Global | Seattle, WA

Responsibilities
• Own release train, SDLC governance, and dependency management across engineering teams
• Coordinate architecture reviews and CI/CD adoption for enterprise cloud migration on AWS
• Lead cross-functional technical delivery with executive stakeholder management
• Facilitate PI planning, release calendar, and deployment governance

Requirements
• 8+ years technical program management in global enterprise environments
• Strong release governance, technical execution, and architecture coordination
• Experience with Fortune 500 client delivery and steering committee reporting
"""

use_sample_jd = st.checkbox("Use sample TPM job description", key="sample_jd")

jd_text: str | None = None
if jd_uploaded is not None:
    jd_text = jd_uploaded.read().decode("utf-8", errors="replace")
elif use_sample_jd:
    jd_text = SAMPLE_JD_TPM
else:
    jd_text = st.text_area(
        "Or paste job description text",
        height=200,
        placeholder="Paste JD responsibilities and requirements…",
        key="jd_paste",
    )
    if not jd_text or not jd_text.strip():
        jd_text = None

if jd_text and jd_text.strip():
    job = match_engine.parse_job(jd_text)
    match_result = match_engine.match(profile, job)

    jcol1, jcol2 = st.columns(2)
    with jcol1:
        st.write("**Job title**", job.title or "—")
        st.write(
            "**Primary role family**",
            ROLE_FAMILIES[job.primary_role_family].display_name,
        )
        st.write("**Required seniority**", job.required_seniority.value.replace("_", " ").title())
        st.write("**Governance intensity**", f"{job.governance_intensity:.0%}")
        flags = []
        if job.is_product_heavy:
            flags.append("Product-heavy")
        if job.is_operations_heavy:
            flags.append("Operations-heavy")
        if job.is_architecture_heavy:
            flags.append("Architecture-heavy")
        if job.is_release_governance_heavy:
            flags.append("Release governance")
        if job.is_ai_transformation:
            flags.append("AI transformation")
        st.write("**Job profile flags**", ", ".join(flags) or "—")
    with jcol2:
        st.write("**Fit components**")
        st.write(f"• Capability similarity: {match_result.capability_similarity:.0%}")
        st.write(f"• Eligibility fit: {match_result.eligibility_fit:.0%}")
        st.write(f"• Seniority fit: {match_result.seniority_fit:.0%}")
        st.write(f"• Transformation fit: {match_result.transformation_fit:.0%}")
        st.write(f"• Architecture fit: {match_result.architecture_fit:.0%}")
        st.write(f"• Governance fit: {match_result.governance_fit:.0%}")
        if match_result.dominant_match_dimensions:
            st.write(
                "**Dominant match dimensions**",
                ", ".join(match_result.dominant_match_dimensions[:5]),
            )

    st.subheader("Capability radar — candidate vs job")
    render_capability_overlap_radar(profile, job)

    st.subheader("Match score & explainability")
    render_job_match_summary(match_result.to_dict())

    with st.expander("Job match (JSON)", expanded=False):
        st.json(
            {
                "job": job.model_dump(mode="json"),
                "match": match_result.to_dict(),
            }
        )
else:
    st.info("Upload, paste, or enable the sample JD to run candidate ↔ job matching.")

st.subheader("CandidateProfile (JSON)")
st.code(json.dumps(profile.model_dump(mode="json"), indent=2), language="json")
