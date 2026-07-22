from unittest.mock import patch, MagicMock
import pytest
from app.services.scoring_engine import score_interview
from app.models.schemas import InterviewState, InterviewPlan, InterviewSection, ScoringCriterion, Difficulty, ResumeBundle, ParsedResume, ResumeAnalysis, KnowledgeGraph

@patch("app.services.scoring_engine.llm.complete_json")
def test_score_interview_weighting_logic(mock_complete_json):
    """
    Test that the scoring engine correctly clamps values and calculates the weighted overall score 
    deterministically without relying on the LLM's math.
    """
    # 1. Setup mock plan with 3 criteria
    plan = InterviewPlan(
        sections=[],
        total_estimated_turns=5,
        scoring_criteria=[
            ScoringCriterion(name="Communication", weight=0.5, description="clear"),
            ScoringCriterion(name="Technical Depth", weight=0.3, description="deep"),
            ScoringCriterion(name="Problem Solving", weight=0.2, description="smart")
        ]
    )
    state = InterviewState(
        session_id="test",
        resume=ResumeBundle(
            parsed=ParsedResume(raw_text="", skills=[], projects=[], experience=[], education=[], certifications=[], achievements=[]),
            analysis=ResumeAnalysis(summary="", strengths=[], gaps=[], ats_issues=[]),
            graph=KnowledgeGraph(nodes=[], edges=[])
        ),
        plan=plan,
        transcript=[]
    )

    # 2. Mock LLM response (notice the hallucinated over-max score of 12.0)
    mock_complete_json.return_value = {
        "scores": [
            {"criterion_name": "Communication", "score": 12.0, "justification": "", "location": ""},
            {"criterion_name": "Technical Depth", "score": 5.0, "justification": "", "location": ""},
            {"criterion_name": "Problem Solving", "score": 8.0, "justification": "", "location": ""}
        ]
    }

    # 3. Execution
    result = score_interview(state)

    # 4. Verification
    assert len(result.scores) == 3
    
    # 12.0 should be clamped to 10.0
    comm_score = next(s for s in result.scores if s.criterion_name == "Communication")
    assert comm_score.score == 10.0

    # Weighted Overall = (10.0 * 0.5) + (5.0 * 0.3) + (8.0 * 0.2)
    # = 5.0 + 1.5 + 1.6 = 8.1
    # Expected: 8.10
    
    assert result.weighted_overall == 8.1

@patch("app.services.scoring_engine.llm.complete_json")
def test_score_interview_hallucinated_criteria(mock_complete_json):
    """
    Test that the scoring engine raises an error if the LLM hallucinated entirely different criteria
    and didn't match the plan (fails the 75% coverage check).
    """
    plan = InterviewPlan(
        sections=[],
        total_estimated_turns=5,
        scoring_criteria=[
            ScoringCriterion(name="Real Criterion 1", weight=0.5, description="real"),
            ScoringCriterion(name="Real Criterion 2", weight=0.5, description="real")
        ]
    )
    state = InterviewState(
        session_id="test",
        resume=ResumeBundle(
            parsed=ParsedResume(raw_text="", skills=[], projects=[], experience=[], education=[], certifications=[], achievements=[]),
            analysis=ResumeAnalysis(summary="", strengths=[], gaps=[], ats_issues=[]),
            graph=KnowledgeGraph(nodes=[], edges=[])
        ),
        plan=plan,
        transcript=[]
    )

    # Mock LLM returning completely wrong criteria
    mock_complete_json.return_value = {
        "scores": [
            {"criterion_name": "Fake 1", "score": 8.0, "justification": "", "location": ""},
            {"criterion_name": "Fake 2", "score": 5.0, "justification": "", "location": ""}
        ]
    }

    with pytest.raises(ValueError, match="Failed to generate valid scores after"):
        score_interview(state, retries=1)
