"""
Module 4: Resume-Based Question Generator — generates the opening question,
grounded in the resume AND the first section of the Interview Plan (module
5), so the very first question is already aimed at the planner's intended
starting point rather than picked independently of it.
"""

from app.services.llm_client import llm
from app.models.schemas import ResumeBundle, InterviewSection

SYSTEM_PROMPT = """You are an experienced technical interviewer opening a \
mock interview. You're given the candidate's resume AND the planned first \
section of the interview (its objective and target topics). Generate \
exactly ONE strong opening question that serves that section's objective \
and targets one of its target_topics — grounded in a specific project, \
skill, or experience entry from the resume, not a generic textbook \
question. You will also be provided with 'Unsupported Skills', which are \
skills the candidate claims but doesn't demonstrate in their projects or \
experience. You may choose to probe an unsupported skill if it aligns \
with the section's objective.

Return JSON: {"question": "...", "topic": "the specific project/skill this targets", "rationale": "why you chose this question"}
"""


def generate_opening_question(resume: ResumeBundle, first_section: InterviewSection) -> tuple[str, str, str]:
    parsed = resume.parsed
    unsupported_skills = resume.graph.unsupported_skills()
    user = (
        f"Section objective: {first_section.objective}\n"
        f"Section target topics: {first_section.target_topics}\n"
        f"Section target difficulty: {first_section.target_difficulty.value}\n\n"
        f"Projects: {[p.model_dump() for p in parsed.projects]}\n"
        f"Experience: {[e.model_dump() for e in parsed.experience]}\n"
        f"Skills: {parsed.skills}\n"
        f"Unsupported Skills: {unsupported_skills}"
    )
    result = llm.complete_json(SYSTEM_PROMPT, user)
    return result["question"], result["topic"], result.get("rationale", "")
