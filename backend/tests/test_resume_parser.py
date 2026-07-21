"""
Tests for resume_parser: text extraction (PDF + DOCX), parse-quality
confidence flag, and end-to-end parse_resume with mocked LLM.
"""

import pytest
from unittest.mock import patch, MagicMock
from docx import Document as DocxDocument
import io

from app.services.resume_parser import (
    extract_text,
    _assess_parse_quality,
    _SECTION_HEADER_RE,
    _MIN_TEXT_LENGTH,
    parse_resume,
)
from app.models.schemas import ParsedResume


# ---------------------------------------------------------------------------
# Fixtures: realistic resume text blobs
# ---------------------------------------------------------------------------

# A "clean" resume: clear section headers, standard structure.
CLEAN_RESUME_TEXT = """\
John Doe
john.doe@email.com | (555) 123-4567 | linkedin.com/in/johndoe

Summary
Experienced full-stack developer with 6+ years building scalable web apps.

Skills
Python, JavaScript, TypeScript, React, Node.js, PostgreSQL, Docker, AWS,
Redis, GraphQL, REST APIs, CI/CD, Git

Experience
Senior Software Engineer — Acme Corp
Jan 2021 – Present
- Designed and built a real-time analytics dashboard serving 50K DAU using
  React, Node.js, and PostgreSQL.
- Migrated legacy REST endpoints to GraphQL, reducing average payload size
  by 40%.
- Led adoption of Docker-based CI/CD pipeline cutting deploy time from 45
  min to 8 min.

Software Engineer — Widgets Inc.
Jun 2018 – Dec 2020
- Built a customer-facing invoice portal (React, TypeScript, AWS Lambda)
  processing $2M/month in transactions.
- Implemented Redis caching layer reducing API p99 latency from 1.2s to
  180ms.

Projects
AssetFlow — Personal finance tracker built with Next.js, Prisma, and
Tailwind CSS. Features real-time portfolio sync via Plaid API.
Role: Solo developer

Education
B.S. Computer Science — State University, 2014–2018

Certifications
AWS Certified Solutions Architect – Associate
"""

# A "messy" resume: mixed columns, tables rendered as pipes, no clear
# "Experience" header, unconventional structure — the kind that trips up
# naive parsers.
MESSY_RESUME_TEXT = """\
PRIYA SHARMA                              priya.sharma@mail.com
+91-9876543210                            Bangalore, India

CAREER PROFILE
Versatile backend engineer, 4 yrs exp building microservices and data
pipelines.  Comfortable across the stack but strongest in distributed
systems and observability.

WHAT I'VE WORKED ON
---
Fintech Startup (SDE-2) | 2022-present
  - Rebuilt payments reconciliation service (Go, gRPC, Kafka) handling
    12M txn/day
  - Owned SLO dashboards (Prometheus + Grafana); drove p99 from 800ms
    to 220ms
  - Mentored 2 junior engineers on code review and system design

DataCorp (Backend Eng) | 2020-2022
  - Built ETL pipelines (Python, Airflow, BigQuery) ingesting 4 TB/day
    from 30+ sources
  - Designed schema migration strategy for a 200-table Postgres DB
    with zero downtime
  - On-call rotation lead; reduced MTTR by 35% through runbook
    automation

TECH STACK
Go | Python | Java | SQL | Kafka | gRPC | Kubernetes | Docker |
Prometheus | Grafana | BigQuery | Airflow | PostgreSQL | Redis | Git

SIDE PROJECTS
  cost-guardian — K8s cost anomaly detector (Go + Prometheus exporter)
  lingua-api — Language-learning flashcard API (FastAPI, spaced-repetition
  algo, SQLite)

EDUCATION
B.Tech Computer Science — IIT Hyderabad, 2016-2020
"""


# ---------------------------------------------------------------------------
# Helper: build a minimal .docx file in-memory
# ---------------------------------------------------------------------------

def _make_docx_bytes(paragraphs: list[str], table_rows: list[list[str]] | None = None) -> bytes:
    """Create a .docx file in memory and return its bytes."""
    doc = DocxDocument()
    for para in paragraphs:
        doc.add_paragraph(para)
    if table_rows:
        table = doc.add_table(rows=len(table_rows), cols=len(table_rows[0]))
        for r_idx, row_data in enumerate(table_rows):
            for c_idx, cell_text in enumerate(row_data):
                table.rows[r_idx].cells[c_idx].text = cell_text
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ===========================================================================
# 1. extract_text tests
# ===========================================================================

class TestExtractText:
    """Verify .docx and .txt extraction paths (PDF requires a real PDF,
    tested separately if needed — pypdf is already proven in production)."""

    def test_docx_paragraphs_extracted(self):
        docx_bytes = _make_docx_bytes(["Hello world", "Skills", "Python, Go"])
        text = extract_text(docx_bytes, "resume.docx")
        assert "Hello world" in text
        assert "Python, Go" in text

    def test_docx_tables_extracted(self):
        """Tables in .docx (common for two-column resumes) should be captured."""
        docx_bytes = _make_docx_bytes(
            ["Summary"],
            table_rows=[
                ["Company", "Role", "Duration"],
                ["Acme Corp", "SDE-2", "2021-present"],
            ],
        )
        text = extract_text(docx_bytes, "resume.DOCX")  # uppercase extension
        assert "Acme Corp" in text
        assert "SDE-2" in text

    def test_txt_fallback(self):
        text = extract_text(b"plain text resume\nSkills: Python", "resume.txt")
        assert "plain text resume" in text
        assert "Skills: Python" in text

    def test_unknown_extension_treated_as_txt(self):
        text = extract_text(b"some content", "resume.rtf")
        assert "some content" in text


# ===========================================================================
# 2. _assess_parse_quality tests
# ===========================================================================

class TestAssessParseQuality:

    def test_clean_resume_high_confidence(self):
        result = {
            "skills": ["Python", "React", "Docker"],
            "projects": [{"name": "AssetFlow"}],
            "experience": [{"company": "Acme"}],
        }
        low_conf, notes = _assess_parse_quality(CLEAN_RESUME_TEXT, result)
        assert low_conf is False
        assert notes == []

    def test_short_text_triggers_low_confidence(self):
        result = {"skills": ["Python", "Go"], "projects": [{"name": "X"}], "experience": [{"company": "Y"}]}
        low_conf, notes = _assess_parse_quality("John Doe", result)
        assert low_conf is True
        assert any("very short" in n for n in notes)

    def test_no_section_headers_triggers_low_confidence(self):
        # Long enough text but no recognisable headers
        raw = "Lorem ipsum dolor sit amet. " * 20
        result = {"skills": ["A", "B"], "projects": [{"name": "C"}], "experience": [{"company": "D"}]}
        low_conf, notes = _assess_parse_quality(raw, result)
        assert low_conf is True
        assert any("section headers" in n.lower() for n in notes)

    def test_near_empty_extraction_triggers_low_confidence(self):
        result = {"skills": [], "projects": [], "experience": []}
        low_conf, notes = _assess_parse_quality(CLEAN_RESUME_TEXT, result)
        assert low_conf is True
        assert any("very few items" in n for n in notes)

    def test_one_item_total_still_triggers(self):
        """Exactly 1 item across skills+projects+experience is still suspicious."""
        result = {"skills": ["Python"], "projects": [], "experience": []}
        low_conf, notes = _assess_parse_quality(CLEAN_RESUME_TEXT, result)
        assert low_conf is True

    def test_two_items_does_not_trigger_extraction_note(self):
        """2 items should NOT trigger the near-empty extraction note."""
        result = {"skills": ["Python", "Go"], "projects": [], "experience": []}
        low_conf, notes = _assess_parse_quality(CLEAN_RESUME_TEXT, result)
        # Should not have the extraction note
        assert not any("very few items" in n for n in notes)

    def test_messy_resume_with_good_extraction_is_still_flagged_for_headers(self):
        """The messy resume uses 'WHAT I'VE WORKED ON' instead of 'Experience',
        but it DOES have 'EDUCATION' — so header check should pass."""
        result = {"skills": ["Go", "Python"], "projects": [{"name": "cost-guardian"}], "experience": [{"company": "Fintech"}]}
        low_conf, notes = _assess_parse_quality(MESSY_RESUME_TEXT, result)
        # "EDUCATION" is present → header check should NOT trigger
        assert not any("section headers" in n.lower() for n in notes)
        assert low_conf is False

    def test_multiple_flags_can_fire_simultaneously(self):
        result = {"skills": [], "projects": [], "experience": []}
        low_conf, notes = _assess_parse_quality("hi", result)
        assert low_conf is True
        assert len(notes) == 3  # short text + no headers + near-empty extraction


# ===========================================================================
# 3. End-to-end parse_resume with mocked LLM
# ===========================================================================

# Realistic LLM return for the clean resume
_CLEAN_LLM_RESULT = {
    "skills": ["Python", "JavaScript", "TypeScript", "React", "Node.js",
               "PostgreSQL", "Docker", "AWS", "Redis", "GraphQL",
               "REST APIs", "CI/CD", "Git"],
    "projects": [
        {
            "name": "AssetFlow",
            "description": "Personal finance tracker with real-time portfolio sync via Plaid API.",
            "technologies": ["Next.js", "Prisma", "Tailwind CSS", "Plaid API"],
            "role": "Solo developer",
        }
    ],
    "experience": [
        {
            "company": "Acme Corp",
            "title": "Senior Software Engineer",
            "duration": "Jan 2021 – Present",
            "bullets": [
                "Designed and built a real-time analytics dashboard serving 50K DAU.",
                "Migrated legacy REST endpoints to GraphQL, reducing payload size by 40%.",
                "Led Docker-based CI/CD pipeline adoption cutting deploy time from 45 min to 8 min.",
            ],
            "technologies": ["React", "Node.js", "PostgreSQL", "GraphQL", "Docker"],
        },
        {
            "company": "Widgets Inc.",
            "title": "Software Engineer",
            "duration": "Jun 2018 – Dec 2020",
            "bullets": [
                "Built customer-facing invoice portal processing $2M/month.",
                "Implemented Redis caching layer reducing API p99 latency from 1.2s to 180ms.",
            ],
            "technologies": ["React", "TypeScript", "AWS Lambda", "Redis"],
        },
    ],
    "education": [
        {
            "institution": "State University",
            "degree": "B.S. Computer Science",
            "field": "Computer Science",
            "duration": "2014–2018",
        }
    ],
    "certifications": ["AWS Certified Solutions Architect – Associate"],
    "achievements": [],
}

# Realistic LLM return for the messy resume
_MESSY_LLM_RESULT = {
    "skills": ["Go", "Python", "Java", "SQL", "Kafka", "gRPC", "Kubernetes",
               "Docker", "Prometheus", "Grafana", "BigQuery", "Airflow",
               "PostgreSQL", "Redis", "Git"],
    "projects": [
        {
            "name": "cost-guardian",
            "description": "K8s cost anomaly detector.",
            "technologies": ["Go", "Prometheus"],
            "role": None,
        },
        {
            "name": "lingua-api",
            "description": "Language-learning flashcard API with spaced-repetition.",
            "technologies": ["FastAPI", "SQLite"],
            "role": None,
        },
    ],
    "experience": [
        {
            "company": "Fintech Startup",
            "title": "SDE-2",
            "duration": "2022-present",
            "bullets": [
                "Rebuilt payments reconciliation service handling 12M txn/day.",
                "Owned SLO dashboards; drove p99 from 800ms to 220ms.",
                "Mentored 2 junior engineers.",
            ],
            "technologies": ["Go", "gRPC", "Kafka", "Prometheus", "Grafana"],
        },
        {
            "company": "DataCorp",
            "title": "Backend Engineer",
            "duration": "2020-2022",
            "bullets": [
                "Built ETL pipelines ingesting 4 TB/day from 30+ sources.",
                "Designed zero-downtime schema migration for 200-table Postgres DB.",
                "Reduced MTTR by 35% through runbook automation.",
            ],
            "technologies": ["Python", "Airflow", "BigQuery", "PostgreSQL"],
        },
    ],
    "education": [
        {
            "institution": "IIT Hyderabad",
            "degree": "B.Tech Computer Science",
            "field": "Computer Science",
            "duration": "2016-2020",
        }
    ],
    "certifications": [],
    "achievements": [],
}


class TestParseResumeEndToEnd:
    """Full parse_resume calls with the LLM mocked out. Validates that
    skills/projects/experience are non-empty for both clean and messy
    resumes, and that the confidence flag is set correctly."""

    @patch("app.services.resume_parser.llm")
    def test_clean_resume_parses_fully(self, mock_llm):
        mock_llm.complete_json.return_value = _CLEAN_LLM_RESULT

        result = parse_resume(CLEAN_RESUME_TEXT.encode(), "john_doe_resume.txt")

        assert isinstance(result, ParsedResume)
        assert len(result.skills) > 0, "Skills should be non-empty for a clean resume"
        assert len(result.projects) > 0, "Projects should be non-empty for a clean resume"
        assert len(result.experience) > 0, "Experience should be non-empty for a clean resume"
        assert result.low_confidence is False
        assert result.parse_quality_notes == []

    @patch("app.services.resume_parser.llm")
    def test_messy_resume_parses_fully(self, mock_llm):
        mock_llm.complete_json.return_value = _MESSY_LLM_RESULT

        result = parse_resume(MESSY_RESUME_TEXT.encode(), "priya_sharma.txt")

        assert isinstance(result, ParsedResume)
        assert len(result.skills) > 0, "Skills should be non-empty even for a messy resume"
        assert len(result.projects) > 0, "Projects should be non-empty even for a messy resume"
        assert len(result.experience) > 0, "Experience should be non-empty even for a messy resume"
        # Messy resume has "EDUCATION" header → headers check passes
        # Good extraction → extraction check passes
        # Long enough text → short-text check passes
        assert result.low_confidence is False

    @patch("app.services.resume_parser.llm")
    def test_malformed_resume_flags_low_confidence(self, mock_llm):
        """Simulate a near-empty / image-based PDF where text extraction
        yields almost nothing and the LLM returns empty lists."""
        mock_llm.complete_json.return_value = {
            "skills": [],
            "projects": [],
            "experience": [],
            "education": [],
            "certifications": [],
            "achievements": [],
        }

        result = parse_resume(b"Name: ???", "bad_scan.txt")

        assert result.low_confidence is True
        assert len(result.parse_quality_notes) > 0

    @patch("app.services.resume_parser.llm")
    def test_docx_clean_resume(self, mock_llm):
        """End-to-end with a real .docx file (no tables)."""
        mock_llm.complete_json.return_value = _CLEAN_LLM_RESULT
        docx_bytes = _make_docx_bytes(CLEAN_RESUME_TEXT.split("\n"))

        result = parse_resume(docx_bytes, "john_doe.docx")

        assert isinstance(result, ParsedResume)
        assert len(result.skills) > 0
        assert len(result.projects) > 0
        assert len(result.experience) > 0
        # raw_text should contain resume content extracted from docx
        assert "John Doe" in result.raw_text

    @patch("app.services.resume_parser.llm")
    def test_docx_with_tables(self, mock_llm):
        """Ensure table content in .docx is extracted into raw_text."""
        mock_llm.complete_json.return_value = _MESSY_LLM_RESULT
        docx_bytes = _make_docx_bytes(
            ["Priya Sharma", "Skills"],
            table_rows=[
                ["Go", "Python", "Kafka"],
                ["Docker", "K8s", "Grafana"],
            ],
        )

        result = parse_resume(docx_bytes, "priya.docx")

        assert "Go" in result.raw_text
        assert "Grafana" in result.raw_text

    @patch("app.services.resume_parser.llm")
    def test_schema_shape_unchanged(self, mock_llm):
        """Verify that the original fields are all present and the only new
        fields are low_confidence and parse_quality_notes."""
        mock_llm.complete_json.return_value = _CLEAN_LLM_RESULT

        result = parse_resume(CLEAN_RESUME_TEXT.encode(), "test.txt")

        # Original fields
        assert hasattr(result, "raw_text")
        assert hasattr(result, "skills")
        assert hasattr(result, "projects")
        assert hasattr(result, "experience")
        assert hasattr(result, "education")
        assert hasattr(result, "certifications")
        assert hasattr(result, "achievements")
        # New fields
        assert hasattr(result, "low_confidence")
        assert hasattr(result, "parse_quality_notes")

        # Confirm serialization shape
        data = result.model_dump()
        expected_keys = {
            "raw_text", "skills", "projects", "experience", "education",
            "certifications", "achievements", "low_confidence",
            "parse_quality_notes",
        }
        assert set(data.keys()) == expected_keys
