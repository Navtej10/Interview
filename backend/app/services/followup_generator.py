"""
Module for determining the next followup strategy based on a candidate's answer.
Extracted for testability and organization, but currently inlined into the
main interview engine prompt to avoid double LLM calls per turn.
"""

from app.models.schemas import InterviewState
from app.services.llm_client import llm
from app.services.conversation_memory import summarize_if_needed

STRATEGY_PROMPT_FRAGMENT = """\
Strategy options:
- "deepen": Use when the candidate demonstrates meaningful understanding. Dig further into the same topic (ask for a harder edge case, a tradeoff they made, why they chose X over Y). Only increase difficulty when justified by demonstrated competence.
- "simplify": Use when the candidate partially understands something but has gaps, or is struggling. Move one conceptual layer down (e.g. ask what data they were caching before discussing caching strategy). Do not make the question childish.
- "follow_up_tangent": Use when the candidate introduces an interesting concrete detail (e.g. "we used batching"). Ask a quick targeted follow-up on that specific detail before moving on.
- "pivot": Use when the current topic has been sufficiently explored, the answer reveals a better topic, the current line of questioning is no longer productive, or the interview needs to move toward another planned section.
- "transition": Use when you have gathered sufficient evidence for the current section and it is time to move to the NEXT section. When using this, provide a natural conversational transition in your question."""


def decide_followup_strategy(state: InterviewState, candidate_answer: str) -> dict:
    """
    Decides the followup strategy based on the candidate's answer.
    Returns a dict with keys: 'strategy' and 'reasoning'.
    
    NOTE: Currently this is for standalone testing. In production, 
    interview_engine.py inlines STRATEGY_PROMPT_FRAGMENT to avoid the latency 
    of a second LLM call. Once this logic is sufficiently robust, we can 
    evaluate the latency trade-off of using this as a discrete first step 
    before generating the actual question.
    """
    
    sys_prompt = f"""\
You are an expert technical interviewer analyzing a candidate's latest answer.
Given the transcript and their latest answer, choose the single best followup strategy.

{STRATEGY_PROMPT_FRAGMENT}

Return JSON exactly:
{{"strategy": "deepen|pivot|simplify|follow_up_tangent|transition", "reasoning": "one sentence explaining why"}}
"""

    transcript_text = summarize_if_needed(state, max_tokens=1500)
    
    user = (
        f"Transcript so far:\n{transcript_text}\n\n"
        f"Candidate's latest answer: {candidate_answer}"
    )

    try:
        result = llm.complete_json(sys_prompt, user)
        # Ensure fallback if it outputs something weird
        if result.get("strategy") not in ["deepen", "pivot", "simplify", "follow_up_tangent", "transition"]:
            return {"strategy": "deepen", "reasoning": "Fallback due to invalid model output"}
        return {
            "strategy": result["strategy"],
            "reasoning": result.get("reasoning", "No reasoning provided.")
        }
    except Exception:
        return {"strategy": "deepen", "reasoning": "Fallback due to error"}
