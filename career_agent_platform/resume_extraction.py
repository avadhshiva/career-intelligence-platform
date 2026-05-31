"""Phase 5A resume upload extraction via embedded deterministic ResumeParser."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from career_intelligence_engine.parsing.resume_parser import ResumeParseError, ResumeParser


@dataclass(frozen=True)
class ResumeExtractionResult:
    success: bool
    resume_text: str = ""
    error: str | None = None
    error_reason: str | None = None


def extract_resume_from_upload(filename: str, content: bytes) -> ResumeExtractionResult:
    """Extract normalized resume text from an uploaded file using ResumeParser only."""
    suffix = Path(filename).suffix.lower()
    parser = ResumeParser()

    try:
        if suffix == ".pdf":
            parsed = parser.parse_pdf(content)
        elif suffix == ".docx":
            parsed = parser.parse_docx(content)
        elif suffix == ".txt":
            if not content:
                return ResumeExtractionResult(
                    success=False,
                    error="Resume file is empty.",
                    error_reason="empty_extraction",
                )
            parsed = parser.parse_text(content.decode("utf-8", errors="replace"))
        else:
            return ResumeExtractionResult(
                success=False,
                error=(
                    f"Unsupported file type '{suffix}'. "
                    f"Supported: {', '.join(sorted(ResumeParser.SUPPORTED_EXTENSIONS))}"
                ),
                error_reason="unsupported_file",
            )
    except ResumeParseError as exc:
        return ResumeExtractionResult(
            success=False,
            error=str(exc),
            error_reason=exc.reason,
        )
    except Exception as exc:
        return ResumeExtractionResult(
            success=False,
            error=f"Resume parsing failed: {exc}",
            error_reason="parsing_failure",
        )

    text = parsed.raw_text.strip()
    if not text:
        return ResumeExtractionResult(
            success=False,
            error="No resume text available after parsing.",
            error_reason="empty_extraction",
        )
    return ResumeExtractionResult(success=True, resume_text=text)
