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
from app.models.schemas import ResumeBundle, InterviewPlan, InterviewSection, ScoringCriterion, CompanyStyleProfile

SYSTEM_PROMPT = """You are planning a technical mock interview based on a \
candidate's resume. You MUST design exactly 5 sections that follow this realistic progression:

1. Introduction / Warm-up: Greet the candidate naturally, briefly explain the interview structure, and ask them to introduce themselves or 1-2 light questions about their background.
2. Background / Resume Discussion: Explore their education, projects, internships, work experience, and skills based heavily on their resume.
3. Technical Interview: Progressively harder technical questions based on the target job/role and technologies in their resume.
4. Behavioral / Situational Questions: Test problem solving, teamwork, handling failure, conflict, etc.
5. Interview Ending: Ask if they have anything to add, allow them to ask a final question, thank them, and gracefully close the interview.

Assign an objective, target topics (prioritizing substantial projects and unsupported skills), and difficulty to each section. \
Keep total_estimated_turns realistic for a short practice session (e.g. 2-3 intro, 2-4 background, 5-8 technical, 2-3 behavioral, 1-2 closing).

Also define a scoring strategy: 3-5 criteria that together weight to 1.0, \
covering both technical substance, communication, and behavioral aspects.

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
    raw_sections = result.get("sections", [])
    sections = []
    for s in raw_sections:
        if "target_difficulty" in s:
            diff = str(s["target_difficulty"]).lower()
            if diff not in ("easy", "medium", "hard"):
                if "hard" in diff:
                    s["target_difficulty"] = "hard"
                elif "easy" in diff:
                    s["target_difficulty"] = "easy"
                else:
                    s["target_difficulty"] = "medium"
        sections.append(InterviewSection(**s))
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


def generate_plan(resume: ResumeBundle, company_profile: CompanyStyleProfile = None, seniority: str = "mid") -> InterviewPlan:
    parsed = resume.parsed
    unsupported = resume.graph.unsupported_skills()

    company_context = ""
    if company_profile:
        mix = company_profile.question_mix
        
        # Apply seniority modifier shift
        modifier = company_profile.seniority_modifiers.get(seniority, company_profile.seniority_modifiers.get("mid"))
        if modifier:
            shift = modifier.question_mix_shift
            b = max(0, mix.behavioral + (shift.behavioral or 0.0))
            t = max(0, mix.technical + (shift.technical or 0.0))
            c = max(0, mix.case_or_system_design + (shift.case_or_system_design or 0.0))
            f = max(0, mix.culture_fit + (shift.culture_fit or 0.0))
            total = b + t + c + f
            if total > 0:
                mix.behavioral = b / total
                mix.technical = t / total
                mix.case_or_system_design = c / total
                mix.culture_fit = f / total
                
        formats = ", ".join(company_profile.signature_formats)
        company_context = (
            f"\n\nCOMPANY STYLE GUIDELINES:\n"
            f"You are conducting a '{company_profile.company}' style interview.\n"
            f"Question Mix Targets: {mix.behavioral*100}% behavioral, {mix.technical*100}% technical, {mix.case_or_system_design*100}% system design, {mix.culture_fit*100}% culture fit.\n"
            f"Signature Formats to include: {formats}.\n"
            f"Please adapt the section targets and overall plan structure to heavily reflect these targets."
        )

    user = (
        f"Resume summary: {resume.analysis.summary}\n"
        f"Projects: {[p.name for p in parsed.projects]}\n"
        f"Experience: {[f'{e.title} @ {e.company}' for e in parsed.experience]}\n"
        f"Skills: {parsed.skills}\n"
        f"Skills with no clear project/experience backing: {unsupported or 'none'}"
        f"{company_context}"
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
