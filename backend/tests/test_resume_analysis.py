"""
Tests for resume_analysis: LLM prompt tightening (severity, precise locations),
deterministic cross-check via knowledge_graph.unsupported_skills(), and
the hybrid analyze() pipeline.
"""

from unittest.mock import patch
from app.services.resume_analysis import (
    analyze,
    _build_unsupported_skill_gaps,
)
from app.models.schemas import (
    ParsedResume,
    ResumeGap,
    ResumeAnalysis,
    KnowledgeGraph,
    GraphNode,
    GraphEdge,
    Severity,
    ResumeProject,
    ResumeExperience,
    ResumeEducation,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_parsed_resume(
    skills: list[str] | None = None,
    projects: list[dict] | None = None,
    experience: list[dict] | None = None,
) -> ParsedResume:
    """Convenience builder with sensible defaults."""
    return ParsedResume(
        raw_text="(test text)",
        skills=skills or ["Python", "React", "Docker", "Terraform"],
        projects=[
            ResumeProject(**(p | {"technologies": p.get("technologies", [])}))
            for p in (projects or [
                {"name": "AssetFlow", "description": "Finance app", "technologies": ["React", "Python"]},
            ])
        ],
        experience=[
            ResumeExperience(**(e | {"bullets": e.get("bullets", []), "technologies": e.get("technologies", [])}))
            for e in (experience or [
                {"company": "Acme Corp", "title": "SDE-2", "bullets": ["Built stuff"], "technologies": ["Python", "Docker"]},
            ])
        ],
        education=[ResumeEducation(institution="MIT", degree="B.S. CS")],
        certifications=[],
        achievements=[],
    )


def _make_graph_with_unsupported(
    supported_skills: list[str],
    all_skills: list[str],
) -> KnowledgeGraph:
    """Build a minimal graph where only `supported_skills` have a 'demonstrates'
    edge. The rest are unsupported."""
    nodes = []
    edges = []
    for skill in all_skills:
        sid = f"skill:{skill.lower()}"
        nodes.append(GraphNode(id=sid, label=skill, type="skill"))
    for skill in supported_skills:
        tid = f"tech:{skill.lower()}"
        sid = f"skill:{skill.lower()}"
        nodes.append(GraphNode(id=tid, label=skill, type="technology"))
        edges.append(GraphEdge(source=tid, target=sid, relation="demonstrates"))
    return KnowledgeGraph(nodes=nodes, edges=edges)


# A realistic LLM response with severity + precise locations
_SAMPLE_LLM_RESULT = {
    "summary": "Full-stack developer with 4 years of experience.",
    "strengths": ["Strong Python background", "Clear project descriptions"],
    "gaps": [
        {
            "category": "missing_metric",
            "location": "Experience > Acme Corp > bullet 1",
            "issue": "No quantitative impact mentioned.",
            "suggestion": "Add metrics like latency reduction or user growth.",
            "severity": "high",
        },
        {
            "category": "unsupported_skill",
            "location": "Skills > Terraform",
            "issue": "Terraform listed but not used in any project or experience.",
            "suggestion": "Add a project or experience entry demonstrating Terraform.",
            "severity": "high",
        },
        {
            "category": "vague_description",
            "location": "Projects > AssetFlow > description",
            "issue": "Description is too brief to understand scope.",
            "suggestion": "Expand with architecture choices, scale, or outcome.",
            "severity": "medium",
        },
    ],
    "ats_issues": ["Inconsistent date format across experience entries"],
}


# ===========================================================================
# 1. _build_unsupported_skill_gaps tests
# ===========================================================================

class TestBuildUnsupportedSkillGaps:

    def test_appends_skills_llm_missed(self):
        """If the graph says 'React' is unsupported but the LLM didn't flag it,
        the cross-check should add a gap for React."""
        graph = _make_graph_with_unsupported(
            supported_skills=["Python"],
            all_skills=["Python", "React", "Docker"],
        )
        llm_gaps: list[ResumeGap] = []  # LLM found nothing

        extra = _build_unsupported_skill_gaps(graph, llm_gaps)

        unsupported_skills = {g.location.split(">")[-1].strip() for g in extra}
        assert "React" in unsupported_skills
        assert "Docker" in unsupported_skills
        assert "Python" not in unsupported_skills  # Python IS supported

    def test_does_not_duplicate_llm_flagged_skills(self):
        """If the LLM already flagged 'Terraform' as unsupported, the
        cross-check should NOT duplicate it."""
        graph = _make_graph_with_unsupported(
            supported_skills=["Python"],
            all_skills=["Python", "Terraform"],
        )
        llm_gaps = [
            ResumeGap(
                category="unsupported_skill",
                location="Skills > Terraform",
                issue="Not demonstrated.",
                suggestion="Add evidence.",
                severity=Severity.high,
            )
        ]

        extra = _build_unsupported_skill_gaps(graph, llm_gaps)

        assert len(extra) == 0, "Should not duplicate Terraform"

    def test_case_insensitive_dedup(self):
        """Deduplication should be case-insensitive: 'terraform' == 'Terraform'."""
        graph = _make_graph_with_unsupported(
            supported_skills=[],
            all_skills=["Terraform"],
        )
        llm_gaps = [
            ResumeGap(
                category="unsupported_skill",
                location="Skills > terraform",  # lowercase
                issue="Not demonstrated.",
                suggestion="Add evidence.",
                severity=Severity.high,
            )
        ]

        extra = _build_unsupported_skill_gaps(graph, llm_gaps)
        assert len(extra) == 0

    def test_all_supported_returns_empty(self):
        """If every skill is supported, cross-check returns nothing."""
        graph = _make_graph_with_unsupported(
            supported_skills=["Python", "React"],
            all_skills=["Python", "React"],
        )

        extra = _build_unsupported_skill_gaps(graph, [])
        assert extra == []

    def test_gap_fields_are_correct(self):
        """Each deterministic gap should have category=unsupported_skill,
        severity=high, and a properly formatted location."""
        graph = _make_graph_with_unsupported(
            supported_skills=[],
            all_skills=["Kubernetes"],
        )

        extra = _build_unsupported_skill_gaps(graph, [])

        assert len(extra) == 1
        gap = extra[0]
        assert gap.category == "unsupported_skill"
        assert gap.severity == Severity.high
        assert gap.location == "Skills > Kubernetes"
        assert "Kubernetes" in gap.issue
        assert "Kubernetes" in gap.suggestion

    def test_ignores_non_unsupported_skill_llm_gaps(self):
        """LLM gaps with other categories should not affect deduplication."""
        graph = _make_graph_with_unsupported(
            supported_skills=[],
            all_skills=["Docker"],
        )
        llm_gaps = [
            ResumeGap(
                category="missing_metric",
                location="Experience > Acme Corp > bullet 1",
                issue="No metrics.",
                suggestion="Add numbers.",
                severity=Severity.medium,
            )
        ]

        extra = _build_unsupported_skill_gaps(graph, llm_gaps)
        assert len(extra) == 1  # Docker should still be flagged


# ===========================================================================
# 2. Severity field tests
# ===========================================================================

class TestSeverityField:

    def test_severity_enum_values(self):
        assert Severity.low == "low"
        assert Severity.medium == "medium"
        assert Severity.high == "high"

    def test_resume_gap_accepts_severity(self):
        gap = ResumeGap(
            category="vague_description",
            location="Projects > AssetFlow",
            issue="Too vague.",
            suggestion="Be specific.",
            severity=Severity.low,
        )
        assert gap.severity == Severity.low

    def test_resume_gap_defaults_to_medium(self):
        gap = ResumeGap(
            category="vague_description",
            location="Projects > AssetFlow",
            issue="Too vague.",
            suggestion="Be specific.",
        )
        assert gap.severity == Severity.medium

    def test_severity_serializes_as_string(self):
        gap = ResumeGap(
            category="ats_issue",
            location="Certifications",
            issue="Test.",
            suggestion="Fix.",
            severity=Severity.high,
        )
        data = gap.model_dump()
        assert data["severity"] == "high"


# ===========================================================================
# 3. End-to-end analyze() with mocked LLM
# ===========================================================================

class TestAnalyzeEndToEnd:

    @patch("app.services.resume_analysis.llm")
    def test_hybrid_analysis_merges_llm_and_deterministic_gaps(self, mock_llm):
        """The LLM flags Terraform but misses React. The graph says both are
        unsupported. The final gaps should contain Terraform (from LLM) and
        React (from deterministic cross-check), but NOT duplicate Terraform."""
        mock_llm.complete_json.return_value = _SAMPLE_LLM_RESULT

        parsed = _make_parsed_resume(
            skills=["Python", "React", "Docker", "Terraform"],
        )
        # Only Python and Docker are demonstrated in projects/experience
        graph = _make_graph_with_unsupported(
            supported_skills=["Python", "Docker"],
            all_skills=["Python", "React", "Docker", "Terraform"],
        )

        result = analyze(parsed, graph)

        assert isinstance(result, ResumeAnalysis)

        # All LLM gaps should be present
        llm_categories = [g.category for g in result.gaps if g.location.startswith("Experience") or g.location.startswith("Projects")]
        assert "missing_metric" in llm_categories
        assert "vague_description" in llm_categories

        # Terraform: flagged by LLM, should appear exactly once
        terraform_gaps = [g for g in result.gaps if "Terraform" in g.location or "terraform" in g.location.lower()]
        assert len(terraform_gaps) == 1

        # React: NOT flagged by LLM but IS unsupported in graph → deterministic gap added
        react_gaps = [g for g in result.gaps if "React" in g.location]
        assert len(react_gaps) == 1
        assert react_gaps[0].category == "unsupported_skill"
        assert react_gaps[0].severity == Severity.high

    @patch("app.services.resume_analysis.llm")
    def test_all_gaps_have_severity(self, mock_llm):
        mock_llm.complete_json.return_value = _SAMPLE_LLM_RESULT

        parsed = _make_parsed_resume()
        graph = _make_graph_with_unsupported(
            supported_skills=["Python", "React", "Docker", "Terraform"],
            all_skills=["Python", "React", "Docker", "Terraform"],
        )

        result = analyze(parsed, graph)

        for gap in result.gaps:
            assert gap.severity in (Severity.low, Severity.medium, Severity.high), (
                f"Gap at '{gap.location}' missing valid severity"
            )

    @patch("app.services.resume_analysis.llm")
    def test_all_gaps_have_precise_locations(self, mock_llm):
        """No gap should have a vague location like 'resume body'."""
        mock_llm.complete_json.return_value = _SAMPLE_LLM_RESULT

        parsed = _make_parsed_resume()
        graph = _make_graph_with_unsupported(
            supported_skills=["Python", "React", "Docker", "Terraform"],
            all_skills=["Python", "React", "Docker", "Terraform"],
        )

        result = analyze(parsed, graph)

        vague_locations = {"resume body", "throughout", "general", "resume"}
        for gap in result.gaps:
            assert gap.location.lower() not in vague_locations, (
                f"Gap has vague location: '{gap.location}'"
            )
            # Should contain a ">" separator (structured path)
            assert ">" in gap.location or gap.location in ("Certifications", "Achievements"), (
                f"Gap location '{gap.location}' is not structured"
            )

    @patch("app.services.resume_analysis.llm")
    def test_no_deterministic_gaps_when_all_supported(self, mock_llm):
        """When every skill is backed by project/experience tech, the
        deterministic cross-check adds nothing."""
        llm_result_no_unsupported = {
            "summary": "Strong candidate.",
            "strengths": ["Good coverage"],
            "gaps": [],
            "ats_issues": [],
        }
        mock_llm.complete_json.return_value = llm_result_no_unsupported

        parsed = _make_parsed_resume(skills=["Python"])
        graph = _make_graph_with_unsupported(
            supported_skills=["Python"],
            all_skills=["Python"],
        )

        result = analyze(parsed, graph)
        assert len(result.gaps) == 0

    @patch("app.services.resume_analysis.llm")
    def test_analyze_returns_correct_shape(self, mock_llm):
        mock_llm.complete_json.return_value = _SAMPLE_LLM_RESULT

        parsed = _make_parsed_resume()
        graph = _make_graph_with_unsupported(
            supported_skills=["Python", "React", "Docker", "Terraform"],
            all_skills=["Python", "React", "Docker", "Terraform"],
        )

        result = analyze(parsed, graph)

        assert isinstance(result.summary, str)
        assert isinstance(result.strengths, list)
        assert isinstance(result.gaps, list)
        assert isinstance(result.ats_issues, list)
        assert all(isinstance(g, ResumeGap) for g in result.gaps)
