"""Deterministic Streamlit visualizations for career intelligence UI."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from career_intelligence_engine.models.candidate_profile import CandidateProfile
from career_intelligence_engine.models.job_profile import JobProfile
from career_intelligence_engine.ontology.capability_vectors import (
    CAPABILITY_DIMENSIONS,
    DIMENSION_LABELS,
)
from career_intelligence_engine.ontology.role_families import ROLE_FAMILIES
from career_intelligence_engine.scoring.career_distance import CareerDistanceScorer

# Fixed deterministic palette (ordered by dimension index)
_DIMENSION_COLORS = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
    "#aec7e8",
    "#ffbb78",
    "#98df8a",
    "#ff9896",
    "#c5b0d5",
]


def _ordered_dimensions() -> list[str]:
    return list(CAPABILITY_DIMENSIONS)


def render_capability_radar(profile: CandidateProfile) -> None:
    dims = _ordered_dimensions()
    values = [float(profile.capability_vector.get(d, 0.0)) for d in dims]
    labels = [DIMENSION_LABELS.get(d, d) for d in dims]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values + [values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name="Candidate",
            line_color=_DIMENSION_COLORS[0],
            fillcolor="rgba(31, 119, 180, 0.25)",
        )
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=False,
        margin=dict(l=40, r=40, t=40, b=40),
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_dimension_lists(profile: CandidateProfile) -> None:
    trace = profile.explanations.get("score_trace") or []
    primary_row = next((r for r in trace if r.get("is_primary")), {})
    dominant = primary_row.get("dominant_dimensions") or []
    weak = primary_row.get("weak_dimensions") or []
    missing = primary_row.get("missing_dimensions") or []

    c1, c2, c3 = st.columns(3)
    with c1:
        st.write("**Dominant dimensions**")
        st.write(", ".join(dominant) or "—")
    with c2:
        st.write("**Weak dimensions**")
        st.write(", ".join(weak) or "—")
    with c3:
        st.write("**Missing dimensions**")
        st.write(", ".join(missing) or "—")


def render_eligibility_matrix(profile: CandidateProfile) -> None:
    matrix = profile.explanations.get("eligibility_matrix") or {}
    if not matrix:
        st.info("No eligibility matrix available.")
        return
    rows = []
    for family_id in sorted(matrix.keys()):
        entry = matrix[family_id]
        if not isinstance(entry, dict):
            continue
        display = family_id
        for fid, defn in ROLE_FAMILIES.items():
            if fid.value == family_id:
                display = defn.display_name
                break
        rows.append(
            {
                "Role family": display,
                "Primary eligible": entry.get(
                    "primary_eligible", entry.get("eligible_for_primary")
                ),
                "Adjacency eligible": entry.get(
                    "adjacency_eligible", entry.get("eligible_for_adjacency")
                ),
                "Ranking eligible": entry.get(
                    "ranking_eligible", entry.get("eligible_for_ranking")
                ),
            }
        )
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_score_breakdown(profile: CandidateProfile) -> None:
    trace = profile.explanations.get("score_trace") or []
    if not trace:
        return
    rows = sorted(trace, key=lambda r: -(r.get("final_score") or 0))[:10]
    families = [r.get("display_name", r.get("role_family")) for r in rows]
    ontology = [float(r.get("ontology_score", 0)) for r in rows]
    vector = [float(r.get("vector_score", 0)) for r in rows]
    final = [float(r.get("final_score", 0)) for r in rows]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Ontology", x=families, y=ontology, marker_color="#1f77b4"))
    fig.add_trace(go.Bar(name="Vector (cosine)", x=families, y=vector, marker_color="#ff7f0e"))
    fig.add_trace(go.Bar(name="Final proximity", x=families, y=final, marker_color="#2ca02c"))
    fig.update_layout(
        barmode="group",
        yaxis_title="Score",
        height=420,
        margin=dict(b=120),
        legend=dict(orientation="h"),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_confidence_analysis(profile: CandidateProfile) -> None:
    conf = profile.confidence_result
    if conf is None:
        conf_data = profile.explanations.get("confidence") or {}
    else:
        conf_data = conf.to_dict()

    if not conf_data:
        st.info("No confidence analysis available.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Confidence score", f"{conf_data.get('confidence_score', 0):.0%}")
    c2.metric("Level", conf_data.get("confidence_level", "—"))
    c3.metric("Ambiguity", f"{conf_data.get('ambiguity_score', 0):.2f}")
    c4.metric("Top gap", f"{conf_data.get('top_gap', 0):.2f}")
    st.caption(
        f"Evidence density: {conf_data.get('evidence_density', 0):.2f}"
    )


def render_contamination_warnings(profile: CandidateProfile) -> None:
    signals = profile.explanations.get("contamination_signals") or []
    if not signals:
        st.success("No contamination signals detected.")
        return
    for sig in signals:
        family = sig.get("family", "Unknown")
        score = sig.get("contamination_score", 0)
        reasons = sig.get("reasons") or []
        st.warning(f"**{family}** (score {score:.2f})")
        for reason in reasons:
            st.write(f"• {reason}")


def render_ranking_breakdown(profile: CandidateProfile) -> None:
    scorer = CareerDistanceScorer()
    ranked = scorer.rank_role_families(profile)
    rows = [
        {
            "Rank": i + 1,
            "Role family": ROLE_FAMILIES[fid].display_name,
            "Proximity": round(result.proximity, 4),
            "Distance": round(
                getattr(result, "semantic_distance", None) or result.distance, 4
            ),
        }
        for i, (fid, result) in enumerate(ranked[:10])
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_capability_overlap_radar(
    profile: CandidateProfile,
    job: JobProfile,
) -> None:
    """Side-by-side candidate vs job capability radar."""
    dims = _ordered_dimensions()
    cand_values = [float(profile.capability_vector.get(d, 0.0)) for d in dims]
    job_values = [float(job.capability_vector.get(d, 0.0)) for d in dims]
    labels = [DIMENSION_LABELS.get(d, d) for d in dims]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=cand_values + [cand_values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name="Candidate",
            line_color=_DIMENSION_COLORS[0],
            fillcolor="rgba(31, 119, 180, 0.2)",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=job_values + [job_values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name="Job",
            line_color=_DIMENSION_COLORS[1],
            fillcolor="rgba(255, 127, 14, 0.2)",
        )
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        legend=dict(orientation="h"),
        margin=dict(l=40, r=40, t=40, b=40),
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_job_match_summary(match: dict[str, Any]) -> None:
    """Render match score metrics and strengths/gaps table."""
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall match", f"{match.get('overall_match_score', 0):.0%}")
    c2.metric("Capability similarity", f"{match.get('capability_similarity', 0):.0%}")
    c3.metric("Confidence", f"{match.get('confidence', 0):.0%}")
    c4.metric("Gate passed", "Yes" if match.get("gate_passed") else "No")

    st.write(match.get("fit_summary", ""))

    rows = []
    for label, key in (
        ("Strength", "strengths"),
        ("Gap", "gaps"),
        ("Risk", "risks"),
        ("Resume improvement", "recommended_resume_improvements"),
    ):
        for item in match.get(key) or []:
            rows.append({"Category": label, "Detail": item})
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_gap_analysis(profile: CandidateProfile) -> None:
    gap = profile.explanations.get("gap_analysis_primary") or {}
    if not gap:
        return
    st.write(f"**Target:** {gap.get('target_display_name', '—')}")
    if gap.get("missing_dimensions"):
        st.write("**Missing:**", ", ".join(gap["missing_dimensions"]))
    if gap.get("weak_dimensions"):
        st.write("**Weak:**", ", ".join(gap["weak_dimensions"]))
    for item in gap.get("resume_strengthening") or []:
        st.info(item)
