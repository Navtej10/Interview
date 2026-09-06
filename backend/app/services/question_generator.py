"""
Module 4: Resume-Based Question Generator — generates the opening question,
grounded in the resume AND the first section of the Interview Plan (module
5), so the very first question is already aimed at the planner's intended
starting point rather than picked independently of it.
"""

from app.services.llm_client import llm
from app.models.schemas import ResumeBundle, InterviewSection

SYSTEM_PROMPT = """You are an experienced technical interviewer opening a \
mock interview. You're given the planned first section of the interview \
(an Introduction / Warm-up section). Generate a short greeting AND exactly \
ONE opening question.

GREETING (1-2 sentences):
- Thank the candidate for joining.
- Briefly explain that the interview will move from background questions, \
into technical questions, and then behavioral questions, before wrapping up.
- Warm and natural, not robotic or scripted-sounding.

OPENING QUESTION:
- Must ask about the candidate's professional background, motivations, or \
career direction in GENERAL terms only — e.g. "Could you walk me through \
your background and what led you into software engineering?"
- CRITICAL: Do NOT reference any specific technology, framework, domain \
niche, project name, or industry area from their resume (e.g. do not say \
"AR", "Metaverse", "React", "the XYZ project"). Those belong to the \
Background/Resume Discussion section later, not here.
- Do NOT ask overly generic or casual icebreakers (e.g. "How are you \
today?", "What are your hobbies?").
- The goal is purely to get them talking about who they are professionally \
before any evaluation begins.

Return JSON exactly:
{"greeting": "...", "question": "...", "topic": "introduction", "rationale": "why you chose this question"}
"""


def generate_opening_question(resume: ResumeBundle, first_section: InterviewSection) -> tuple[str, str, str, str]:
    user = (
        f"Section objective: {first_section.objective}\n"
        f"Section target difficulty: {first_section.target_difficulty.value}\n"
    )
    result = llm.complete_json(SYSTEM_PROMPT, user)
    return result["greeting"], result["question"], result["topic"], result.get("rationale", "")
