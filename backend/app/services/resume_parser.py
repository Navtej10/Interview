"""
Module 1: Resume Parser — pure structured extraction. No judgment/opinions
here (that's resume_analysis.py). Supports PDF and DOCX.
"""

import io
import re
from pypdf import PdfReader
from docx import Document

from app.services.llm_client import llm
from app.models.schemas import ParsedResume, ResumeProject, ResumeExperience, ResumeEducation

SYSTEM_PROMPT = """You extract structured information from a resume. Be \
thorough and literal — extract what's there, don't judge quality or \
completeness (that happens in a separate step). For each project and \
experience entry, list the specific technologies mentioned.

Return JSON exactly:
{
  "skills": ["...", "..."],
  "projects": [{"name": "...", "description": "...", "technologies": ["..."], "role": "..." | null}],
  "experience": [{"company": "...", "title": "...", "duration": "..." | null, "bullets": ["..."], "technologies": ["..."]}],
  "education": [{"institution": "...", "degree": "...", "field": "..." | null, "duration": "..." | null}],
  "certifications": ["...", "..."],
  "achievements": ["...", "..."]
}
"""


def extract_text(file_bytes: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if name.endswith(".docx"):
        doc = Document(io.BytesIO(file_bytes))
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))
        return "\n".join(parts)
    # .txt / plain fallback
    return file_bytes.decode("utf-8", errors="ignore")



# Section headers commonly found in resumes — used for parse-quality heuristic.
_SECTION_HEADER_RE = re.compile(
    r"(?:experience|education|skills|projects|certifications|"
    r"work\s*history|employment|qualifications|summary|objective|"
    r"professional\s*experience|technical\s*skills|achievements)",
    re.IGNORECASE,
)

# If the extracted text is shorter than this, it's likely a scan/image PDF
# or a near-empty file.
_MIN_TEXT_LENGTH = 80


def _assess_parse_quality(
    raw_text: str, result: dict
) -> tuple[bool, list[str]]:
    """Return (low_confidence, notes) based on heuristics."""
    notes: list[str] = []

    # 1. Raw text suspiciously short
    if len(raw_text.strip()) < _MIN_TEXT_LENGTH:
        notes.append(
            f"Extracted text is very short ({len(raw_text.strip())} chars) "
            "— the file may be image-based, corrupt, or nearly empty."
        )

    # 2. No recognisable section headers
    if not _SECTION_HEADER_RE.search(raw_text):
        notes.append(
            "No standard resume section headers detected (e.g. Experience, "
            "Education, Skills). The resume may use non-standard formatting."
        )

    # 3. LLM extraction returned near-empty lists
    extracted_items = (
        len(result.get("skills", []))
        + len(result.get("projects", []))
        + len(result.get("experience", []))
    )
    if extracted_items <= 1:
        notes.append(
            "LLM extraction returned very few items "
            f"(skills + projects + experience = {extracted_items}). "
            "The resume content may not have been parsed correctly."
        )

    return (len(notes) > 0, notes)


def parse_resume(file_bytes: bytes, filename: str) -> ParsedResume:
    raw_text = extract_text(file_bytes, filename)

    result = llm.complete_json(SYSTEM_PROMPT, f"Resume text:\n\n{raw_text}", max_tokens=4000)

    low_confidence, parse_quality_notes = _assess_parse_quality(raw_text, result)

    return ParsedResume(
        raw_text=raw_text,
        skills=result["skills"],
        projects=[ResumeProject(**p) for p in result["projects"]],
        experience=[ResumeExperience(**e) for e in result["experience"]],
        education=[ResumeEducation(**e) for e in result["education"]],
        certifications=result["certifications"],
        achievements=result["achievements"],
        low_confidence=low_confidence,
        parse_quality_notes=parse_quality_notes,
    )

