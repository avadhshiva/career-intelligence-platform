"""Compact UI chips for metrics and status — HTML helpers."""

from __future__ import annotations

from presentation.labels import Badge


_BADGE_CLASS = {
    "success": "ji-badge-success",
    "info": "ji-badge-info",
    "warning": "ji-badge-warning",
    "error": "ji-badge-muted",
    "secondary": "ji-badge-muted",
}


def status_chip_html(badge: Badge) -> str:
    css = _BADGE_CLASS.get(badge.tone, "ji-badge-muted")
    return f'<span class="ji-badge {css}">{badge.label}</span>'


_METRICS_ROW_STYLE = (
    "display:flex;gap:0.5rem;justify-content:flex-end;flex-wrap:wrap;margin-top:0.15rem;"
)
_METRIC_CHIP_STYLE = (
    "display:flex;flex-direction:column;align-items:flex-start;gap:0.12rem;"
    "padding:0.4rem 0.7rem;border-radius:8px;"
    "border:1px solid rgba(49,51,63,0.1);background:rgba(248,250,252,0.9);min-width:5rem;"
)
_METRIC_LABEL_STYLE = (
    "display:block;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.04em;"
    "color:rgba(49,51,63,0.55);font-weight:500;line-height:1.15;white-space:nowrap;"
)
_METRIC_VALUE_STYLE = (
    "display:block;font-size:1rem;font-weight:600;color:rgba(49,51,63,0.92);"
    "line-height:1.25;font-variant-numeric:tabular-nums;white-space:nowrap;"
)


def metric_chips_html(*, fit: str, confidence: str) -> str:
    """Fit/confidence chips — block layout so labels never run into values."""
    return (
        f'<div class="ji-metrics" style="{_METRICS_ROW_STYLE}" '
        'role="group" aria-label="Match scores">'
        f'<div class="ji-metric ji-metric-fit" style="{_METRIC_CHIP_STYLE}">'
        f'<span class="ji-metric-label" style="{_METRIC_LABEL_STYLE}">Fit</span>'
        f'<span class="ji-metric-value" style="{_METRIC_VALUE_STYLE}" '
        f'aria-label="Fit score">{fit}</span>'
        "</div>"
        f'<div class="ji-metric ji-metric-confidence" style="{_METRIC_CHIP_STYLE}">'
        f'<span class="ji-metric-label" style="{_METRIC_LABEL_STYLE}">Confidence</span>'
        f'<span class="ji-metric-value" style="{_METRIC_VALUE_STYLE}" '
        f'aria-label="Confidence score">{confidence}</span>'
        "</div>"
        "</div>"
    )


def role_subline_html(company: str, location: str, badge_label: str) -> str:
    parts = [p for p in (company, location, badge_label) if p]
    text = " • ".join(parts)
    return f'<p class="ji-role-subline">{text}</p>'
