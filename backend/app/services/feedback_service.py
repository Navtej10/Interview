from app.services.llm_client import llm
from app.models.schemas import InterviewState, FeedbackReport, ScoringResult
from app.services import session_store
from app.services.scoring_engine import score_interview, _transcript_text
import json

REPORT_SYSTEM_PROMPT = """You are an expert technical interviewer producing a comprehensive, evidence-based feedback report based strictly on the provided transcript.
Do NOT invent abilities or deficiencies that were never tested. Do NOT penalize the candidate for grammar or accent.

You have been provided with the pre-calculated scores for the candidate, as well as an explicit Termination Reason. 

CRITICAL EARLY TERMINATION RULES:
- If Termination Reason indicates the interview ended early (e.g. 'early_insufficient_evidence', 'early_repeated_non_answers'), explicitly acknowledge this in the overall summary.
- Do NOT claim the candidate lacks knowledge in areas that were planned but not reached. Instead, place them in the 'unassessed' bucket.
- Do NOT penalize the candidate for topics the interview did not reach. Focus your feedback only on what was actually discussed.
- Fill out the 'early_termination_context' if the interview ended early.

CRITICAL EVIDENCE RULES:
- Technical and communication weaknesses MUST be backed by evidence (quote or description of the exact moment).
- Resume credibility must be segmented. If a claim was never tested, mark it 'unverified', NOT false.

Return JSON exactly matching this structure (omit the comments):
{
  "overall_performance": {
    "summary": "...",
    "completion_status": "...",
    "strongest_areas": ["..."],
    "weakest_areas": ["..."]
  },
  "technical_knowledge": {
    "technical_correctness": "...",
    "depth_of_understanding": "...",
    "implementation_details": "...",
    "fundamentals": "...",
    "tradeoffs": "...",
    "debugging_problem_solving": "...",
    "system_design": "..."
  },
  "communication": {
    "clarity": "...",
    "structure": "...",
    "conciseness": "...",
    "directness": "...",
    "explanation_ability": "...",
    "concrete_examples": "..."
  },
  "reasoning_ability": {
    "problem_breakdown": "...",
    "explaining_reasoning": "...",
    "evaluating_alternatives": "...",
    "reasoning_tradeoffs": "...",
    "handling_followups": "...",
    "adaptability": "..."
  },
  "project_ownership": {
    "what_built": "...",
    "responsibilities": "...",
    "technical_decisions": "...",
    "challenges": "...",
    "outcomes": "..."
  },
  "resume_credibility": {
    "supported_claims": ["..."],
    "partially_supported_claims": ["..."],
    "unverified_claims": ["..."],
    "inconsistencies": ["..."]
  },
  "technical_weaknesses": [
    {"description": "...", "evidence": "..."}
  ],
  "communication_weaknesses": [
    {"description": "...", "evidence": "..."}
  ],
  "interview_behavior": {
    "patterns": ["..."]
  },
  "confidence_levels": {
    "high_confidence": ["topic1..."],
    "medium_confidence": ["..."],
    "low_confidence": ["..."],
    "unassessed": ["..."]
  },
  "early_termination_context": {
    "termination_reason": "...",
    "meaningful_answers_collected": 0,
    "unassessed_dimensions": ["..."],
    "assessment_reliability": "..."
  }
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
    termination_reason = state.termination_reason.value if state.termination_reason else "normal_completion"
    user_prompt = f"Termination Reason: {termination_reason}\n\nScores:\n{scores_text}\n\nTranscript:\n{_transcript_text(state)}"
    
    result = llm.complete_json(
        REPORT_SYSTEM_PROMPT,
        user_prompt,
        max_tokens=2000,
    )
    
    result["scores"] = state.final_scores.scores
    result["weighted_overall"] = state.final_scores.weighted_overall
    
    if getattr(state, "company_profile", None):
        result["company_style"] = state.company_profile.company
        result["company_disclaimer"] = state.company_profile.disclaimer
        
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
