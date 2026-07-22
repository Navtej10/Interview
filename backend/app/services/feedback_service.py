from app.services.llm_client import llm
from app.models.schemas import InterviewState, FeedbackReport, ScoringResult
from app.services import session_store
from app.services.scoring_engine import score_interview, _transcript_text
import json

REPORT_SYSTEM_PROMPT = """You are reviewing a completed technical interview \
transcript. Produce a candid, specific feedback report — no generic \
platitudes. Reference actual moments from the transcript.

You have been provided with the pre-calculated scores for the candidate. Use these scores to ground your moment_highlights and strengths/weaknesses.

Return JSON exactly:
{
  "overall_summary": "3-4 sentences",
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "moment_highlights": ["quote or paraphrase a specific moment + what it showed, ..."],
  "recommended_next_steps": ["...", "..."]
}
"""

# Used for the "live debrief" mode — same underlying loop.next_question-style
# engine, different system prompt. The frontend drives this as a normal
# conversational session (see routers/feedback.py), not a one-shot call.
DEBRIEF_SYSTEM_PROMPT = """You are the same interviewer who just conducted \
this technical interview, now giving the candidate a live spoken debrief. \
You have the full transcript and the pre-calculated final scores. Be direct and specific, reference exact \
moments, and let the candidate ask follow-up questions about their \
performance or specific scores. Keep each response conversational and under ~100 words unless \
asked to go deeper."""





def _ensure_scores(state: InterviewState) -> None:
    """Helper to generate and cache scores if they don't exist yet."""
    if state.final_scores is None:
        state.final_scores = score_interview(state)
        session_store.save(state)


def generate_written_report(state: InterviewState) -> FeedbackReport:
    _ensure_scores(state)
    
    scores_text = state.final_scores.model_dump_json(indent=2)
    user_prompt = f"Scores:\n{scores_text}\n\nTranscript:\n{_transcript_text(state)}"
    
    result = llm.complete_json(
        REPORT_SYSTEM_PROMPT,
        user_prompt,
        max_tokens=2000,
    )
    
    result["scores"] = state.final_scores.scores
    result["weighted_overall"] = state.final_scores.weighted_overall
    return FeedbackReport(**result)


def debrief_turn(state: InterviewState, candidate_message: str) -> str:
    """One turn of the live debrief conversation. Called repeatedly from the
    /feedback/debrief endpoint, same pattern as the interview loop."""
    _ensure_scores(state)
    
    scores_text = state.final_scores.model_dump_json(indent=2)
    user = (
        f"Scores:\n{scores_text}\n\n"
        f"Interview transcript:\n{_transcript_text(state)}\n\n"
        f"Candidate says: {candidate_message}"
    )
    return llm.complete(DEBRIEF_SYSTEM_PROMPT, user, max_tokens=400)
