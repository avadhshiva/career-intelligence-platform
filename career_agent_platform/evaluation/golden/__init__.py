"""Committed golden recommendation snapshots for regression governance."""

from __future__ import annotations

from pathlib import Path

GOLDEN_DIR = Path(__file__).resolve().parent

GOLDEN_FIXTURE_IDS: tuple[str, ...] = (
    "tpm_sample",
    "delivery_leadership_sample",
    "platform_engineering_sample",
)
