"""
Tests for knowledge_graph: graph construction from ParsedResume, fuzzy
alias matching (no false positives), unsupported_skills(), and the new
demonstrated_projects_for_skill() helper.

All tests are deterministic — no LLM mocking needed.
"""

import pytest
from app.services.knowledge_graph import (
    build_graph,
    _normalize,
    _is_alias_match,
    _slug,
)
from app.models.schemas import (
    ParsedResume,
    ResumeProject,
    ResumeExperience,
    ResumeEducation,
    KnowledgeGraph,
    GraphNode,
    GraphEdge,
)


# ---------------------------------------------------------------------------
# Fixture builder
# ---------------------------------------------------------------------------

def _make_parsed(
    skills: list[str] | None = None,
    projects: list[dict] | None = None,
    experience: list[dict] | None = None,
) -> ParsedResume:
    """Build a ParsedResume with sensible defaults for graph tests."""
    return ParsedResume(
        raw_text="(fixture)",
        skills=skills or [],
        projects=[
            ResumeProject(
                name=p["name"],
                description=p.get("description", ""),
                technologies=p.get("technologies", []),
                role=p.get("role"),
            )
            for p in (projects or [])
        ],
        experience=[
            ResumeExperience(
                company=e["company"],
                title=e["title"],
                duration=e.get("duration"),
                bullets=e.get("bullets", []),
                technologies=e.get("technologies", []),
            )
            for e in (experience or [])
        ],
        education=[ResumeEducation(institution="MIT", degree="B.S. CS")],
        certifications=[],
        achievements=[],
    )


# ===========================================================================
# 1. _normalize tests
# ===========================================================================

class TestNormalize:

    def test_lowercase(self):
        assert _normalize("React") == "react"

    def test_strips_dotjs(self):
        assert _normalize("React.js") == "react"

    def test_strips_dashjs(self):
        assert _normalize("Vue-js") == "vue"

    def test_strips_trailing_js(self):
        assert _normalize("NodeJS") == "node"

    def test_removes_punctuation(self):
        assert _normalize("C++") == "c"

    def test_preserves_numbers(self):
        assert _normalize("Python3") == "python3"

    def test_empty_string(self):
        assert _normalize("") == ""

    def test_dotnet(self):
        assert _normalize(".NET") == "net"

    def test_underscores(self):
        assert _normalize("scikit_learn") == "scikitlearn"

    def test_javascript_not_mangled(self):
        """'JavaScript' must NOT become 'java' — the 'js' is part of the word."""
        assert _normalize("JavaScript") == "javascript"

    def test_standalone_js_preserved(self):
        """Standalone 'JS' must remain 'js', not become empty."""
        assert _normalize("JS") == "js"


# ===========================================================================
# 2. _is_alias_match tests — the core of correctness
# ===========================================================================

class TestIsAliasMatch:

    # --- True positives: should match ---
    def test_exact_match(self):
        assert _is_alias_match("Python", "python") is True

    def test_reactjs_vs_react(self):
        assert _is_alias_match("React.js", "React") is True

    def test_react_vs_reactjs(self):
        assert _is_alias_match("React", "React.js") is True

    def test_nodejs_vs_node(self):
        assert _is_alias_match("Node.js", "Node") is True

    def test_nodejs_uppercase_vs_nodejs(self):
        assert _is_alias_match("NodeJS", "Node.js") is True

    def test_postgresql_vs_postgres(self):
        assert _is_alias_match("PostgreSQL", "Postgres") is True

    def test_kubernetes_vs_k8s(self):
        assert _is_alias_match("Kubernetes", "K8s") is True

    def test_golang_vs_go(self):
        assert _is_alias_match("Golang", "Go") is True

    def test_go_vs_golang(self):
        assert _is_alias_match("Go", "Golang") is True

    def test_javascript_vs_js(self):
        assert _is_alias_match("JavaScript", "JS") is True

    def test_typescript_vs_ts(self):
        assert _is_alias_match("TypeScript", "TS") is True

    def test_substring_long_forms(self):
        """PostgreSQL contains 'postgres' (≥3 chars both sides)."""
        assert _is_alias_match("PostgreSQL", "Postgres") is True

    # --- True negatives: must NOT match ---
    def test_go_vs_google(self):
        """The original substring bug: 'go' in 'google' → True. Fixed."""
        assert _is_alias_match("Go", "Google") is False

    def test_r_vs_react(self):
        """Single-char 'R' must not match 'React'."""
        assert _is_alias_match("R", "React") is False

    def test_c_vs_css(self):
        assert _is_alias_match("C", "CSS") is False

    def test_sql_vs_nosql(self):
        """'SQL' is only 3 chars but 'NoSQL' contains it — this IS a
        substring match (both ≥3) and is arguably correct. If you don't
        want this, add to the alias table. For now, accept it."""
        # This tests current behaviour, not necessarily desired behaviour
        assert _is_alias_match("SQL", "NoSQL") is True

    def test_empty_tech(self):
        assert _is_alias_match("", "Python") is False

    def test_empty_skill(self):
        assert _is_alias_match("Python", "") is False

    def test_completely_different(self):
        assert _is_alias_match("Docker", "Kubernetes") is False


# ===========================================================================
# 3. build_graph — node/edge creation
# ===========================================================================

class TestBuildGraph:

    def test_all_technologies_become_nodes(self):
        """Every technology in projects and experience must have a node,
        regardless of whether it matches a skill."""
        parsed = _make_parsed(
            skills=["Python"],
            projects=[{"name": "App", "technologies": ["React.js", "GraphQL"]}],
            experience=[{"company": "Acme", "title": "SDE", "technologies": ["Docker", "Terraform"]}],
        )
        graph = build_graph(parsed)

        tech_labels = {n.label for n in graph.nodes if n.type == "technology"}
        assert "React.js" in tech_labels
        assert "GraphQL" in tech_labels
        assert "Docker" in tech_labels
        assert "Terraform" in tech_labels

    def test_all_technologies_have_uses_edge(self):
        """Every tech node must have a 'uses' edge from its parent."""
        parsed = _make_parsed(
            skills=[],
            projects=[{"name": "App", "technologies": ["React", "Node.js"]}],
        )
        graph = build_graph(parsed)

        uses_targets = {e.target for e in graph.edges if e.relation == "uses"}
        react_id = _slug("tech", "React")
        node_id = _slug("tech", "Node.js")
        assert react_id in uses_targets
        assert node_id in uses_targets

    def test_project_node_created(self):
        parsed = _make_parsed(projects=[{"name": "AssetFlow", "technologies": []}])
        graph = build_graph(parsed)
        project_labels = {n.label for n in graph.nodes if n.type == "project"}
        assert "AssetFlow" in project_labels

    def test_experience_node_created(self):
        parsed = _make_parsed(experience=[{"company": "Acme", "title": "SDE-2", "technologies": []}])
        graph = build_graph(parsed)
        exp_labels = {n.label for n in graph.nodes if n.type == "experience"}
        assert "SDE-2 @ Acme" in exp_labels

    def test_skill_nodes_created(self):
        parsed = _make_parsed(skills=["Python", "Go"])
        graph = build_graph(parsed)
        skill_labels = {n.label for n in graph.nodes if n.type == "skill"}
        assert skill_labels == {"Python", "Go"}

    def test_duplicate_tech_across_project_and_experience(self):
        """Same tech in a project and an experience should create ONE tech
        node (via ensure_node dedup) but TWO 'uses' edges."""
        parsed = _make_parsed(
            skills=[],
            projects=[{"name": "App", "technologies": ["Python"]}],
            experience=[{"company": "Acme", "title": "SDE", "technologies": ["Python"]}],
        )
        graph = build_graph(parsed)

        python_nodes = [n for n in graph.nodes if n.type == "technology" and n.label == "Python"]
        assert len(python_nodes) == 1, "Should be exactly one Python tech node"

        uses_edges = [e for e in graph.edges if e.target == python_nodes[0].id and e.relation == "uses"]
        assert len(uses_edges) == 2, "Should have 'uses' edges from both project and experience"


# ===========================================================================
# 4. Fuzzy demonstrates-edge linking
# ===========================================================================

class TestDemonstratesEdges:

    def test_reactjs_demonstrates_react_skill(self):
        """'React.js' in a project should create a 'demonstrates' edge to
        the 'React' skill — the old substring bug would have worked here,
        but _normalize makes it explicit."""
        parsed = _make_parsed(
            skills=["React"],
            projects=[{"name": "App", "technologies": ["React.js"]}],
        )
        graph = build_graph(parsed)

        react_skill_id = _slug("skill", "React")
        demonstrates = [e for e in graph.edges if e.relation == "demonstrates" and e.target == react_skill_id]
        assert len(demonstrates) >= 1, "React.js tech should demonstrate React skill"

    def test_go_does_not_demonstrate_google(self):
        """False positive regression: 'Go' tech must NOT demonstrate a
        hypothetical 'Google' skill."""
        parsed = _make_parsed(
            skills=["Google"],
            projects=[{"name": "CLI", "technologies": ["Go"]}],
        )
        graph = build_graph(parsed)

        google_skill_id = _slug("skill", "Google")
        demonstrates = [e for e in graph.edges if e.relation == "demonstrates" and e.target == google_skill_id]
        assert len(demonstrates) == 0, "Go should NOT demonstrate Google"

    def test_nodejs_demonstrates_node_skill(self):
        parsed = _make_parsed(
            skills=["Node.js"],
            projects=[{"name": "API", "technologies": ["NodeJS"]}],
        )
        graph = build_graph(parsed)

        node_skill_id = _slug("skill", "Node.js")
        demonstrates = [e for e in graph.edges if e.relation == "demonstrates" and e.target == node_skill_id]
        assert len(demonstrates) >= 1

    def test_kubernetes_demonstrates_k8s_skill(self):
        parsed = _make_parsed(
            skills=["K8s"],
            experience=[{"company": "X", "title": "SRE", "technologies": ["Kubernetes"]}],
        )
        graph = build_graph(parsed)

        k8s_skill_id = _slug("skill", "K8s")
        demonstrates = [e for e in graph.edges if e.relation == "demonstrates" and e.target == k8s_skill_id]
        assert len(demonstrates) >= 1

    def test_tech_not_in_skills_has_no_demonstrates_edge(self):
        """A technology that has no matching skill should have zero
        'demonstrates' edges — but SHOULD still have a 'uses' edge."""
        parsed = _make_parsed(
            skills=["Python"],
            projects=[{"name": "App", "technologies": ["Terraform"]}],
        )
        graph = build_graph(parsed)

        terraform_id = _slug("tech", "Terraform")
        demonstrates = [e for e in graph.edges if e.source == terraform_id and e.relation == "demonstrates"]
        uses = [e for e in graph.edges if e.target == terraform_id and e.relation == "uses"]
        assert len(demonstrates) == 0
        assert len(uses) == 1


# ===========================================================================
# 5. unsupported_skills() — graph-export test
# ===========================================================================

class TestUnsupportedSkills:

    def test_exact_fixture_unsupported(self):
        """Build a graph from a known fixture and assert unsupported_skills()
        returns exactly the skills we expect."""
        parsed = _make_parsed(
            skills=["Python", "React", "Docker", "Terraform", "Rust"],
            projects=[
                {"name": "WebApp", "technologies": ["React.js", "Python"]},
            ],
            experience=[
                {"company": "Acme", "title": "SDE", "technologies": ["Python", "Docker"]},
            ],
        )
        graph = build_graph(parsed)

        unsupported = set(graph.unsupported_skills())

        # Python: used in both project and experience → supported
        assert "Python" not in unsupported
        # React: "React.js" in project matches "React" via normalisation → supported
        assert "React" not in unsupported
        # Docker: used in experience → supported
        assert "Docker" not in unsupported
        # Terraform: not in any technology list → unsupported
        assert "Terraform" in unsupported
        # Rust: not in any technology list → unsupported
        assert "Rust" in unsupported

        assert unsupported == {"Terraform", "Rust"}

    def test_all_skills_supported(self):
        parsed = _make_parsed(
            skills=["Python"],
            projects=[{"name": "App", "technologies": ["Python"]}],
        )
        graph = build_graph(parsed)
        assert graph.unsupported_skills() == []

    def test_all_skills_unsupported(self):
        parsed = _make_parsed(
            skills=["Haskell", "Erlang"],
            projects=[{"name": "App", "technologies": ["Python"]}],
        )
        graph = build_graph(parsed)
        assert set(graph.unsupported_skills()) == {"Haskell", "Erlang"}

    def test_no_skills(self):
        parsed = _make_parsed(skills=[], projects=[{"name": "App", "technologies": ["Python"]}])
        graph = build_graph(parsed)
        assert graph.unsupported_skills() == []


# ===========================================================================
# 6. demonstrated_projects_for_skill()
# ===========================================================================

class TestDemonstratedProjectsForSkill:

    def test_returns_projects_that_use_skill(self):
        parsed = _make_parsed(
            skills=["React"],
            projects=[
                {"name": "WebApp", "technologies": ["React"]},
                {"name": "CLI", "technologies": ["Python"]},
            ],
        )
        graph = build_graph(parsed)

        react_skill_id = _slug("skill", "React")
        backers = graph.demonstrated_projects_for_skill(react_skill_id)
        assert "WebApp" in backers
        assert "CLI" not in backers

    def test_returns_experience_entries_too(self):
        parsed = _make_parsed(
            skills=["Docker"],
            experience=[
                {"company": "Acme", "title": "SDE", "technologies": ["Docker"]},
            ],
        )
        graph = build_graph(parsed)

        docker_skill_id = _slug("skill", "Docker")
        backers = graph.demonstrated_projects_for_skill(docker_skill_id)
        assert "SDE @ Acme" in backers

    def test_returns_both_projects_and_experience(self):
        parsed = _make_parsed(
            skills=["Python"],
            projects=[{"name": "DataPipe", "technologies": ["Python"]}],
            experience=[{"company": "BigCo", "title": "Eng", "technologies": ["Python"]}],
        )
        graph = build_graph(parsed)

        python_skill_id = _slug("skill", "Python")
        backers = set(graph.demonstrated_projects_for_skill(python_skill_id))
        assert "DataPipe" in backers
        assert "Eng @ BigCo" in backers

    def test_returns_empty_for_unsupported_skill(self):
        parsed = _make_parsed(
            skills=["Rust"],
            projects=[{"name": "App", "technologies": ["Python"]}],
        )
        graph = build_graph(parsed)

        rust_skill_id = _slug("skill", "Rust")
        assert graph.demonstrated_projects_for_skill(rust_skill_id) == []

    def test_returns_empty_for_nonexistent_id(self):
        parsed = _make_parsed(skills=["Python"])
        graph = build_graph(parsed)
        assert graph.demonstrated_projects_for_skill("skill:does-not-exist") == []

    def test_alias_match_walks_through(self):
        """If project uses 'React.js' and skill is 'React', the alias match
        should create a demonstrates edge, and demonstrated_projects_for_skill
        should walk back through it to find the project."""
        parsed = _make_parsed(
            skills=["React"],
            projects=[{"name": "FrontendApp", "technologies": ["React.js"]}],
        )
        graph = build_graph(parsed)

        react_skill_id = _slug("skill", "React")
        backers = graph.demonstrated_projects_for_skill(react_skill_id)
        assert "FrontendApp" in backers

    def test_inverse_of_unsupported(self):
        """Every supported skill should return a non-empty list from
        demonstrated_projects_for_skill, and every unsupported skill
        should return an empty list."""
        parsed = _make_parsed(
            skills=["Python", "Docker", "Terraform"],
            projects=[{"name": "App", "technologies": ["Python"]}],
            experience=[{"company": "X", "title": "Eng", "technologies": ["Docker"]}],
        )
        graph = build_graph(parsed)

        unsupported = set(graph.unsupported_skills())
        skill_nodes = [n for n in graph.nodes if n.type == "skill"]

        for skill_node in skill_nodes:
            backers = graph.demonstrated_projects_for_skill(skill_node.id)
            if skill_node.label in unsupported:
                assert backers == [], f"{skill_node.label} is unsupported but has backers"
            else:
                assert len(backers) > 0, f"{skill_node.label} is supported but has no backers"
