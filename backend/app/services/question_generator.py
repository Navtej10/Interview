"""
Module 4: Resume-Based Question Generator — generates the opening question,
grounded in the resume AND the first section of the Interview Plan (module
5), so the very first question is already aimed at the planner's intended
starting point rather than picked independently of it.
"""

from app.services.llm_client import llm
from app.models.schemas import ResumeBundle, InterviewSection

SYSTEM_PROMPT = """You are an experienced technical interviewer opening a \
mock interview. You're given the planned first section of the interview. \
Generate exactly ONE opening question. 

CRITICAL: The very first question MUST be a professionally relevant question that helps you understand the candidate's background, motivations, interests, or career direction (e.g., "Could you start by walking me through your background and what led you to pursue computer science?"). \
Do NOT ask overly generic or casual icebreakers (e.g., "How are you today?", "What are your hobbies?"). \
Do NOT mention any specific project, programming languages, technologies, or technical concepts from their resume yet. \
The goal is to establish their professional background and motivations in a conversational way, getting to know them before evaluating technical skills.

Return JSON: {"question": "...", "topic": "introduction", "rationale": "why you chose this question"}
"""


def generate_opening_question(resume: ResumeBundle, first_section: InterviewSection) -> tuple[str, str, str]:
    user = (
        f"Section objective: {first_section.objective}\n"
        f"Section target topics: {first_section.target_topics}\n"
        f"Section target difficulty: {first_section.target_difficulty.value}\n"
    )
    result = llm.complete_json(SYSTEM_PROMPT, user)
    return result["question"], result["topic"], result.get("rationale", "")
