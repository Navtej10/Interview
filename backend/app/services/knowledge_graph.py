"""
Module 3: Resume Knowledge Graph — links projects, experience, technologies,
and claimed skills into a semantic graph for contextual reasoning
(question generation, follow-ups, and the deterministic unsupported-skill
check in KnowledgeGraph.unsupported_skills()).

Deliberately deterministic, not LLM-based: the entities already come from
ParsedResume (module 1), so this is pure linking — cheaper, faster, and
reproducible. No LLM call needed here.
"""

import re
from app.models.schemas import ParsedResume, KnowledgeGraph, GraphNode, GraphEdge


def _slug(prefix: str, text: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return f"{prefix}:{clean}"


# ---------------------------------------------------------------------------
# Normalisation for fuzzy skill ↔ technology matching
# ---------------------------------------------------------------------------

def _normalize(name: str) -> str:
    """Reduce a technology or skill name to a canonical form for comparison.
    Steps:
      1. Strip separator-based suffixes (.js, -js, _js) on the original
      2. Strip uppercase 'JS' suffix (e.g. NodeJS → Node)
      3. Lowercase
      4. Remove all non-alphanumeric characters
    Examples:
      "React.js"   → "react"
      "Node.js"    → "node"
      "NodeJS"     → "node"
      "Vue.js"     → "vue"
      "JavaScript" → "javascript"  (NOT "java")
      "JS"         → "js"          (standalone, not stripped)
      "C++"        → "c"
      "Go"         → "go"
    """
    # Strip separator-suffix first (before lowercasing, so we can be precise)
    # 1. ".js", "-js", "_js" (case-insensitive for the suffix part)
    s = re.sub(r"[.\-_][jJ][sS]$", "", name)
    # 2. Uppercase "JS" at end, but only after a letter/digit (not standalone "JS")
    s = re.sub(r"(?<=[a-zA-Z0-9])JS$", "", s)
    # 3. Lowercase + strip non-alphanumeric
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def _is_alias_match(tech_label: str, skill_label: str) -> bool:
    """Determine whether a technology label should be considered a match for
    a skill label.  Much tighter than raw substring: normalises first, then
    requires an *exact* normalised match.  This catches real aliases
    ("React.js" ↔ "React", "NodeJS" ↔ "Node.js") while avoiding false
    positives ("Go" ↔ "Google", "R" ↔ "React").

    Falls back to substring only when *both* normalised forms are ≥ 3 chars
    and one contains the other — this lets "PostgreSQL" match "Postgres" but
    won't let "Go" match "Golang" (different enough after normalisation).
    We explicitly handle "Go"↔"Golang" via a small alias table instead.
    """
    tn = _normalize(tech_label)
    sn = _normalize(skill_label)

    if not tn or not sn:
        return False

    # Exact normalised match covers most cases
    if tn == sn:
        return True

    # Guarded substring: only when both sides are long enough to be meaningful
    if len(tn) >= 3 and len(sn) >= 3:
        if tn in sn or sn in tn:
            return True

    # Small alias table for known short-name edge cases that normalisation
    # alone can't resolve.  Kept deliberately minimal — add entries only
    # when you hit a real-world mismatch.
    _ALIASES: dict[str, set[str]] = {
        "go":       {"golang"},
        "golang":   {"go"},
        "cpp":      {"c", "cplusplus"},
        "cplusplus":{"cpp", "c"},
        "js":       {"javascript"},
        "javascript":{"js"},
        "ts":       {"typescript"},
        "typescript":{"ts"},
        "k8s":      {"kubernetes"},
        "kubernetes":{"k8s"},
        "postgres": {"postgresql"},
        "postgresql":{"postgres"},
    }
    return sn in _ALIASES.get(tn, set()) or tn in _ALIASES.get(sn, set())


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph(parsed: ParsedResume) -> KnowledgeGraph:
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    def ensure_node(node_id: str, label: str, node_type: str) -> str:
        if node_id not in nodes:
            nodes[node_id] = GraphNode(id=node_id, label=label, type=node_type)
        return node_id

    # --- Skills ---
    skill_ids: dict[str, str] = {}
    for skill in parsed.skills:
        sid = ensure_node(_slug("skill", skill), skill, "skill")
        skill_ids[skill.lower()] = sid

    # --- Projects & their technologies ---
    for project in parsed.projects:
        pid = ensure_node(_slug("project", project.name), project.name, "project")
        for tech in project.technologies:
            tid = ensure_node(_slug("tech", tech), tech, "technology")
            edges.append(GraphEdge(source=pid, target=tid, relation="uses"))

    # --- Experience & their technologies ---
    for exp in parsed.experience:
        eid = ensure_node(
            _slug("experience", f"{exp.company}-{exp.title}"),
            f"{exp.title} @ {exp.company}",
            "experience",
        )
        for tech in exp.technologies:
            tid = ensure_node(_slug("tech", tech), tech, "technology")
            edges.append(GraphEdge(source=eid, target=tid, relation="uses"))

    # --- Link technologies → skills via normalised alias matching ---
    # Every technology node gets checked against every skill; if they're
    # aliases of each other a "demonstrates" edge is created.  This is the
    # only place fuzzy matching happens — the rest of the graph is exact.
    tech_nodes = [n for n in nodes.values() if n.type == "technology"]
    for tech in tech_nodes:
        for skill_label, sid in skill_ids.items():
            if _is_alias_match(tech.label, skill_label):
                edges.append(GraphEdge(source=tech.id, target=sid, relation="demonstrates"))

    return KnowledgeGraph(nodes=list(nodes.values()), edges=edges)

