import pytest
from unittest.mock import patch
from app.models.schemas import (
    InterviewState, ResumeBundle, ParsedResume, ResumeAnalysis, 
    KnowledgeGraph, InterviewPlan, InterviewSection, ScoringCriterion, Difficulty,
    InterviewPhase, TranscriptTurn
)
from app.services.feedback_service import score_interview

@pytest.fixture
def mock_state():
    return InterviewState(
        session_id="test_session",
        resume=ResumeBundle(
            parsed=ParsedResume(
                skills=["python"], projects=[], experience=[], education=[], certifications=[], achievements=[], raw_text="mock text"
            ),
            analysis=ResumeAnalysis(summary="A test candidate", gaps=[], strengths=[], ats_issues=[]),
            graph=KnowledgeGraph(nodes=[], edges=[])
        ),
        plan=InterviewPlan(
            sections=[],
            total_estimated_turns=5,
            scoring_criteria=[
                ScoringCriterion(name="Technical Depth", weight=0.6, description="Depth of knowledge"),
                ScoringCriterion(name="Communication", weight=0.4, description="Clarity")
            ]
        ),
        transcript=[
            TranscriptTurn(role="interviewer", content="Tell me about Python", topic="python"),
            TranscriptTurn(role="candidate", content="It is a programming language.", topic="python")
        ],
        covered_topics=["python"],
        current_difficulty=Difficulty.medium,
        phase=InterviewPhase.COMPLETE,
        turn_count=2,
        is_complete=True
    )

@patch("app.services.feedback_service.llm.complete_json")
def test_score_interview_regression(mock_complete_json, mock_state):
    # Mock LLM returning scores mapped to the criteria
    mock_complete_json.return_value = {
        "scores": [
            {
                "criterion_name": "Technical Depth",
                "score": 0.8,
                "justification": "Good explanation",
                "location": "Transcript > Turn 2"
            },
            {
                "criterion_name": "Communication",
                "score": 0.9,
                "justification": "Very clear",
                "location": "Transcript > Turn 2"
            }
        ]
    }
    
    scores = score_interview(mock_state)
    
    # Verify the response is parsed into the Score schema correctly
    assert len(scores) == 2
    assert scores[0].criterion_name == "Technical Depth"
    assert scores[0].score == 0.8
    assert scores[1].criterion_name == "Communication"
    assert scores[1].score == 0.9
    
    # Sanity check: verify weight math works
    criteria_map = {c.name: c.weight for c in mock_state.plan.scoring_criteria}
    
    total_weighted_score = sum(s.score * criteria_map.get(s.criterion_name, 0.0) for s in scores)
    
    # 0.8 * 0.6 + 0.9 * 0.4 = 0.48 + 0.36 = 0.84
    assert abs(total_weighted_score - 0.84) < 0.001
