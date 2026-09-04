import json
import logging
from app.services.llm_client import llm
from app.models.schemas import InterviewState, ScoringResult, CriterionScore

logger = logging.getLogger(__name__)

SCORING_SYSTEM_PROMPT = """You are an expert technical interviewer evaluating a completed interview transcript.
You have a specific set of scoring criteria. For each criterion, produce a score between 0.0 and 10.0, and a specific justification tying it back to a distinct moment in the transcript.

Return JSON exactly:
{
  "scores": [
    {
      "criterion_name": "Name of criterion",
      "score": 8.5,
      "justification": "Candidate showed strong ...",
      "location": "Transcript > Turn 4 > Python GIL discussion"
    }
  ]
}
"""

def _transcript_text(state: InterviewState) -> str:
    return "\n".join(f"{t.role}: {t.content}" for t in state.transcript)

def score_interview(state: InterviewState, retries: int = 2) -> ScoringResult:
    """Generates criteria-based scores for the completed interview and computes weighted_overall."""
    if not state.plan.scoring_criteria:
        return ScoringResult(scores=[], weighted_overall=0.0)

    criteria_text = "\n".join(f"- {c.name} (weight: {c.weight}): {c.description}" for c in state.plan.scoring_criteria)
    
    company_context = ""
    if getattr(state, "company_profile", None):
        dims = state.company_profile.evaluation_dimensions.copy()
        
        seniority = getattr(state, "inferred_seniority", "mid")
        modifier = state.company_profile.seniority_modifiers.get(seniority, state.company_profile.seniority_modifiers.get("mid"))
        if modifier and modifier.evaluation_emphasis:
            dims.extend(f"{emp} (HEAVY EMPHASIS)" for emp in modifier.evaluation_emphasis)
            
        dims_str = ", ".join(dims)
        company_context = (
            f"\n\nCOMPANY EVALUATION DIMENSIONS ({state.company_profile.company}):\n"
            f"You must explicitly consider these dimensions when assigning scores: {dims_str}\n"
        )
        
    user_prompt = f"Scoring Criteria:\n{criteria_text}{company_context}\n\nTranscript:\n{_transcript_text(state)}"
    
    for attempt in range(retries):
        try:
            result = llm.complete_json(SCORING_SYSTEM_PROMPT, user_prompt, max_tokens=1500)
            
            scores = []
            for s in result.get("scores", []):
                # Clamp score to 0-10
                raw_score = float(s.get("score", 0.0))
                clamped_score = max(0.0, min(10.0, raw_score))
                s["score"] = clamped_score
                scores.append(CriterionScore(**s))

            # Compute weighted overall
            expected_criteria = {c.name: c.weight for c in state.plan.scoring_criteria}
            
            total_weight = 0.0
            weighted_sum = 0.0
            matched_count = 0
            
            for score in scores:
                weight = expected_criteria.get(score.criterion_name)
                if weight is not None:
                    matched_count += 1
                    total_weight += weight
                    weighted_sum += score.score * weight

            # Validate that the LLM matched most criteria (at least 75%)
            if matched_count < len(expected_criteria) * 0.75:
                raise ValueError(f"LLM hallucinated criteria or missed too many. Expected: {list(expected_criteria.keys())}, Got: {[s.criterion_name for s in scores]}")
            
            # Fallback for total_weight just in case math is wonky
            if total_weight == 0:
                total_weight = 1.0

            weighted_overall = weighted_sum / total_weight
            
            return ScoringResult(scores=scores, weighted_overall=round(weighted_overall, 2))
        except Exception as e:
            logger.warning(f"Scoring attempt {attempt + 1} failed: {e}")
            if attempt == retries - 1:
                raise ValueError(f"Failed to generate valid scores after {retries} attempts: {e}")
