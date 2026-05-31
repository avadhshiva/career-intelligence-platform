"""Metric chip HTML structure — prevents Fit80%Confidence95% regressions."""

from __future__ import annotations

from presentation.chips import metric_chips_html


def test_metric_chips_separate_label_and_value_blocks() -> None:
    html = metric_chips_html(fit="80%", confidence="95%")
    assert 'class="ji-metric-label" style=' in html
    assert "Fit</span>" in html
    assert 'aria-label="Fit score">80%</span>' in html
    assert 'class="ji-metric-label" style=' in html
    assert 'aria-label="Confidence score">95%</span>' in html
    assert "Fit80%" not in html.replace(" ", "")
    assert "Confidence95%" not in html.replace(" ", "")
    assert 'style="display:block;' in html
    assert html.count('class="ji-metric ') == 2
    assert "ji-metric-fit" in html
    assert 'aria-label="Fit score"' in html
