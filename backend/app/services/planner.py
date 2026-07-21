"""
Module 5: Interview Planner — decides the interview blueprint UP FRONT,
before any question is asked: sections, per-section objective and target
topics, difficulty distribution, and scoring strategy.

This runs once, at interview start. It's what gives the adaptive loop
(interview_engine.py) something to aim at instead of purely reacting
turn-by-turn — sections carry a target_difficulty and target_topics that
the engine is told to work toward, while still adapting within a section
based on how the candidate is actually doing.
"""

from app.services.llm_client import llm
from app.models.schemas import ResumeBundle, InterviewPlan, InterviewSection, ScoringCriterion

SYSTEM_PROMPT = """You are planning a technical mock interview based on a \
candidate's resume. Design 3-5 sections that together give a well-rounded \
read on this specific candidate — prioritize their most substantial \
projects, any claimed skills that look unsupported by their listed \
experience, and at least one broader technical-reasoning section (system \
design or problem solving) beyond just resume recall. Order sections from \
easier/warm-up to harder. Keep total_estimated_turns realistic for a short \
practice session (aim for 8-14 total turns across all sections).

Also define a scoring strategy: 3-5 criteria that together weight to 1.0, \
covering both technical substance and communication.

Return JSON exactly:
{
  "sections": [
    {"name": "...", "objective": "...", "target_topics": ["..."],
     "target_difficulty": "easy|medium|hard", "estimated_turns": <int>}
  ],
  "scoring_criteria": [
    {"name": "...", "weight": <float>, "description": "..."}
  ]
}
"""


def _build_plan_from_llm_result(result: dict) -> InterviewPlan:
    """Helper to construct and validate an InterviewPlan from LLM JSON output."""
    sections = [InterviewSection(**s) for s in result.get("sections", [])]
    scoring_criteria = [ScoringCriterion(**c) for c in result.get("scoring_criteria", [])]

    # 1. Renormalize weights deterministically if they don't sum to ~1.0
    total_weight = sum(c.weight for c in scoring_criteria)
    if total_weight > 0 and abs(total_weight - 1.0) > 1e-4:
        for c in scoring_criteria:
            c.weight = round(c.weight / total_weight, 4)
    elif total_weight == 0 and scoring_criteria:
        # Fallback if model gives all 0s
        even_weight = round(1.0 / len(scoring_criteria), 4)
        for c in scoring_criteria:
            c.weight = even_weight

    # 2. Recompute total turns rather than trusting a potentially returned field
    total_turns = sum(s.estimated_turns for s in sections)

    return InterviewPlan(
        sections=sections,
        total_estimated_turns=total_turns,
        scoring_criteria=scoring_criteria,
    )


def generate_plan(resume: ResumeBundle) -> InterviewPlan:
    parsed = resume.parsed
    unsupported = resume.graph.unsupported_skills()

    user = (
        f"Resume summary: {resume.analysis.summary}\n"
        f"Projects: {[p.name for p in parsed.projects]}\n"
        f"Experience: {[f'{e.title} @ {e.company}' for e in parsed.experience]}\n"
        f"Skills: {parsed.skills}\n"
        f"Skills with no clear project/experience backing: {unsupported or 'none'}"
    )
    result = llm.complete_json(SYSTEM_PROMPT, user, max_tokens=1800)
    return _build_plan_from_llm_result(result)


REGENERATE_SYSTEM_PROMPT = SYSTEM_PROMPT + """

CRITICAL ADDITION FOR RE-INTERVIEW:
You are generating a plan for a candidate who is practicing AGAIN. 
You will be provided with FEEDBACK FROM A PRIOR SESSION. 
You MUST adjust this new plan to specifically target the areas where the candidate previously struggled or demonstrated weakness, while still providing a well-rounded interview.
"""

def regenerate_plan(resume: ResumeBundle, feedback_from_prior_session: str) -> InterviewPlan:
    parsed = resume.parsed
    unsupported = resume.graph.unsupported_skills()

    user = (
        f"Resume summary: {resume.analysis.summary}\n"
        f"Projects: {[p.name for p in parsed.projects]}\n"
        f"Experience: {[f'{e.title} @ {e.company}' for e in parsed.experience]}\n"
        f"Skills: {parsed.skills}\n"
        f"Skills with no clear project/experience backing: {unsupported or 'none'}\n\n"
        f"FEEDBACK FROM PRIOR SESSION:\n{feedback_from_prior_session}"
    )
    result = llm.complete_json(REGENERATE_SYSTEM_PROMPT, user, max_tokens=1800)
    return _build_plan_from_llm_result(result)


def section_for_question_index(plan: InterviewPlan, question_index: int) -> tuple[InterviewSection, int]:
    """Which section a given question number (0-based, opening question = 0)
    falls into. Deterministic — no LLM call. Once turns run past the plan's
    total, stay in the final section rather than erroring."""
    cumulative = 0
    for i, section in enumerate(plan.sections):
        cumulative += section.estimated_turns
        if question_index < cumulative:
            return section, i
    return plan.sections[-1], len(plan.sections) - 1
