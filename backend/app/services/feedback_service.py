from app.services.llm_client import llm
from app.models.schemas import InterviewState, FeedbackReport, Score
from app.services import session_store
import json

SCORING_SYSTEM_PROMPT = """You are an expert technical interviewer evaluating a completed interview transcript.
You have a specific set of scoring criteria. For each criterion, produce a score between 0.0 and 1.0, and a specific justification tying it back to a distinct moment in the transcript.

Return JSON exactly:
{
  "scores": [
    {
      "criterion_name": "Name of criterion",
      "score": 0.8,
      "justification": "Candidate showed strong ...",
      "location": "Transcript > Turn 4 > Python GIL discussion"
    }
  ]
}
"""

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


def _transcript_text(state: InterviewState) -> str:
    return "\n".join(f"{t.role}: {t.content}" for t in state.transcript)


def score_interview(state: InterviewState) -> list[Score]:
    """Generates criteria-based scores for the completed interview."""
    criteria_text = "\n".join(f"- {c.name} (weight: {c.weight}): {c.description}" for c in state.plan.scoring_criteria)
    user_prompt = f"Scoring Criteria:\n{criteria_text}\n\nTranscript:\n{_transcript_text(state)}"
    
    result = llm.complete_json(SCORING_SYSTEM_PROMPT, user_prompt, max_tokens=1500)
    
    # Parse the returned scores list into the Score schema
    scores = []
    for s in result.get("scores", []):
        scores.append(Score(**s))
    return scores


def _ensure_scores(state: InterviewState) -> None:
    """Helper to generate and cache scores if they don't exist yet."""
    if state.final_scores is None:
        state.final_scores = score_interview(state)
        session_store.save(state)


def generate_written_report(state: InterviewState) -> FeedbackReport:
    _ensure_scores(state)
    
    scores_text = json.dumps([s.model_dump() for s in state.final_scores], indent=2)
    user_prompt = f"Scores:\n{scores_text}\n\nTranscript:\n{_transcript_text(state)}"
    
    result = llm.complete_json(
        REPORT_SYSTEM_PROMPT,
        user_prompt,
        max_tokens=2000,
    )
    
    result["scores"] = state.final_scores
    return FeedbackReport(**result)


def debrief_turn(state: InterviewState, candidate_message: str) -> str:
    """One turn of the live debrief conversation. Called repeatedly from the
    /feedback/debrief endpoint, same pattern as the interview loop."""
    _ensure_scores(state)
    
    scores_text = json.dumps([s.model_dump() for s in state.final_scores], indent=2)
    user = (
        f"Scores:\n{scores_text}\n\n"
        f"Interview transcript:\n{_transcript_text(state)}\n\n"
        f"Candidate says: {candidate_message}"
    )
    return llm.complete(DEBRIEF_SYSTEM_PROMPT, user, max_tokens=400)
