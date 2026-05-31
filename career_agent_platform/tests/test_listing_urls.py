"""Unit tests for deterministic LinkedIn listing URL generation."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, unquote_plus, urlparse

import pytest
import requests

from services.listing_urls import (
    build_linkedin_search_url,
    build_valid_listing_url,
    is_broken_listing_url,
    resolve_listing_url,
    scrub_persisted_listing_urls,
)

_BROKEN_SAMPLES = (
    "https://www.linkedin.com/jobs/search/?currentJobId=4418593028&keywords=TPM",
    "https://www.linkedin.com/jobs/view/4418593028",
    "https://careers.example.com/infosys/tpm-blr-001",
    "https://www.linkedin.com/jobs/search/?keywords=TPM&jobId=4418593028",
)


def test_build_linkedin_search_url_with_company_and_location() -> None:
    url = build_linkedin_search_url(
        normalized_title="Technical Program Manager",
        company_name="Infosys",
        location="Bengaluru",
    )
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert parsed.scheme == "https"
    assert parsed.netloc == "www.linkedin.com"
    assert parsed.path.startswith("/jobs/search/")
    assert unquote_plus(qs["keywords"][0]) == "Technical Program Manager Infosys"
    assert unquote_plus(qs["location"][0]) == "Bengaluru"
    assert "currentJobId" not in url
    assert "jobId" not in url.lower()


def test_build_linkedin_search_url_title_only_when_company_missing() -> None:
    url = build_linkedin_search_url(
        normalized_title="Technical Program Manager",
        company_name="",
        location="Hyderabad",
    )
    qs = parse_qs(urlparse(url).query)
    assert unquote_plus(qs["keywords"][0]) == "Technical Program Manager"
    assert unquote_plus(qs["location"][0]) == "Hyderabad"


def test_build_linkedin_search_url_omits_location_when_missing() -> None:
    url = build_linkedin_search_url(
        normalized_title="Release Manager",
        company_name="Wipro",
        location="",
    )
    qs = parse_qs(urlparse(url).query)
    assert unquote_plus(qs["keywords"][0]) == "Release Manager Wipro"
    assert "location" not in qs


def test_resolve_listing_url_ignores_stale_cached_urls() -> None:
    for stale in _BROKEN_SAMPLES:
        url = resolve_listing_url(
            company="Deloitte",
            role="Enterprise Program Leadership Opportunity",
            location="Bangalore",
            job_url=stale,
        )
        assert "currentJobId" not in url
        assert "/jobs/view/" not in url
        assert "example.com" not in url
        assert "Deloitte" in unquote_plus(parse_qs(urlparse(url).query)["keywords"][0])


def test_is_broken_listing_url_detects_malformed_patterns() -> None:
    for sample in _BROKEN_SAMPLES:
        assert is_broken_listing_url(sample)


def test_build_valid_listing_url_wrapper_matches_entity_builder() -> None:
    direct = build_linkedin_search_url(
        normalized_title="Program Director",
        company_name="HCL",
        location="Chennai",
    )
    wrapped = build_valid_listing_url("Program Director", "HCL", "Chennai")
    assert direct == wrapped


def test_scrub_persisted_listing_urls_removes_cached_fields(tmp_path: Path) -> None:
    payload_path = tmp_path / "review_queue.json"
    payload_path.write_text(
        '{"entries":[{"match_detail":{"job_url":"https://www.linkedin.com/jobs/search/?currentJobId=1&keywords=x"}}]}',
        encoding="utf-8",
    )
    removed = scrub_persisted_listing_urls(tmp_path)
    assert removed == 1
    payload = payload_path.read_text(encoding="utf-8")
    assert "job_url" not in payload


@pytest.mark.parametrize(
    ("title", "company", "location"),
    [
        ("Technical Program Manager", "Infosys", "Bengaluru"),
        ("Release Train Engineer", "Wipro", "Bengaluru"),
        ("Program Director", "HCL", "Chennai"),
        ("AI Program Manager", "Tech Mahindra", "Bengaluru"),
        ("Operations Program Manager", "Amazon", "Hyderabad"),
    ],
)
def test_generated_urls_are_navigable(
    title: str,
    company: str,
    location: str,
) -> None:
    url = build_linkedin_search_url(
        normalized_title=title,
        company_name=company,
        location=location,
    )
    assert not is_broken_listing_url(url)
    response = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0 (compatible; JobIntelligenceTest/1.0)"},
        allow_redirects=True,
    )
    assert response.status_code in {200, 999}
