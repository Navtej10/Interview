"""
Module 2: Resume Analysis Engine — takes a ParsedResume and passes judgment:
weaknesses, missing details, unsupported claims, ATS issues, formatting
problems, improvement suggestions. Deliberately separate from parsing
(module 1) so extraction stays factual and analysis stays opinionated —
you'll want to tune/re-prompt these independently.

This is a *hybrid* module: the LLM provides judgment-heavy analysis, and
a deterministic cross-check via KnowledgeGraph.unsupported_skills() catches
any claimed-but-undemonstrated skills the LLM overlooked.
"""

from app.services.llm_client import llm
from app.models.schemas import (
    ParsedResume, ResumeAnalysis, ResumeGap, KnowledgeGraph, Severity,
)

SYSTEM_PROMPT = """\
You are a strict, experienced technical interviewer and resume reviewer. \
You're given ALREADY-EXTRACTED structured resume data (not raw text) — \
your job is judgment, not extraction. Identify concrete gaps: vague project \
descriptions, missing metrics/impact, skills listed without evidence they \
were used in any project/experience, and formatting or ATS-parseability \
issues (e.g. inconsistent date formats, skills buried in paragraphs instead \
of scannable lists, missing keywords for common ATS filters).

LOCATION REQUIREMENTS — every gap MUST have a precise, machine-mappable \
location string following one of these patterns exactly:
  - "Skills > {skill_name}"
  - "Experience > {company} > bullet {1-indexed number}"
  - "Experience > {company} > duration"
  - "Projects > {project_name}"
  - "Projects > {project_name} > description"
  - "Education > {institution}"
  - "Certifications" or "Achievements"
NEVER use vague locations like "resume body", "throughout", or "general". \
If a gap spans multiple items, emit one gap per item.

SEVERITY — assign one of "low", "medium", or "high" to each gap:
  - high: will likely cause ATS rejection or interviewer red-flag \
(missing metrics on a senior role, skill claimed but never used anywhere)
  - medium: noticeable weakness a reviewer would flag but not a deal-breaker \
(vague bullet, inconsistent date format)
  - low: polish-level improvement (minor wording, optional extra detail)

Don't invent issues that aren't supported by the data given.

Return JSON exactly:
{
  "summary": "2-3 sentence overview of the candidate's background",
  "strengths": ["...", "..."],
  "gaps": [
    {"category": "vague_description|missing_metric|unsupported_skill|ats_issue|formatting",
     "location": "Experience > Acme Corp > bullet 2",
     "issue": "what's wrong",
     "suggestion": "how to fix it",
     "severity": "low|medium|high"}
  ],
  "ats_issues": ["...", "..."]
}
"""


def _build_unsupported_skill_gaps(
    graph: KnowledgeGraph, llm_gaps: list[ResumeGap]
) -> list[ResumeGap]:
    """Deterministic cross-check: any skill that KnowledgeGraph flags as
    unsupported (claimed but never tied to a project/experience technology)
    that the LLM's gaps list didn't already cover gets appended."""
    # Collect skills the LLM already flagged as unsupported
    llm_flagged_skills: set[str] = set()
    for gap in llm_gaps:
        if gap.category == "unsupported_skill":
            # Extract skill name from location like "Skills > React"
            parts = gap.location.split(">")
            if len(parts) >= 2:
                llm_flagged_skills.add(parts[-1].strip().lower())

    extra_gaps: list[ResumeGap] = []
    for skill in graph.unsupported_skills():
        if skill.lower() not in llm_flagged_skills:
            extra_gaps.append(ResumeGap(
                category="unsupported_skill",
                location=f"Skills > {skill}",
                issue=(
                    f'"{skill}" is listed in skills but not mentioned in '
                    f"any project or experience technology list."
                ),
                suggestion=(
                    f"Either add a project/experience entry that demonstrates "
                    f'"{skill}", or remove it from skills to avoid interviewer '
                    f"scrutiny."
                ),
                severity=Severity.high,
            ))
    return extra_gaps


def analyze(parsed: ParsedResume, graph: KnowledgeGraph) -> ResumeAnalysis:
    """Hybrid analysis: LLM judgment + deterministic unsupported-skill check."""
    user = (
        f"Skills: {parsed.skills}\n\n"
        f"Projects: {[p.model_dump() for p in parsed.projects]}\n\n"
        f"Experience: {[e.model_dump() for e in parsed.experience]}\n\n"
        f"Education: {[e.model_dump() for e in parsed.education]}\n\n"
        f"Certifications: {parsed.certifications}\n"
        f"Achievements: {parsed.achievements}"
    )
    result = llm.complete_json(SYSTEM_PROMPT, user, max_tokens=4000)

    llm_gaps = [ResumeGap(**g) for g in result["gaps"]]

    # Deterministic cross-check: append unsupported skills the LLM missed
    deterministic_gaps = _build_unsupported_skill_gaps(graph, llm_gaps)
    all_gaps = llm_gaps + deterministic_gaps

    return ResumeAnalysis(
        summary=result["summary"],
        strengths=result["strengths"],
        gaps=all_gaps,
        ats_issues=result["ats_issues"],
    )

