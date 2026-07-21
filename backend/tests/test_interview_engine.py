import pytest
from unittest.mock import patch
from app.models.schemas import InterviewState, TranscriptTurn, ResumeBundle, ParsedResume, ResumeAnalysis, KnowledgeGraph, InterviewPlan, InterviewSection, Difficulty, InterviewPhase
from app.services.interview_engine import next_question

@pytest.fixture
def mock_state():
    return InterviewState(
        session_id="test_session",
        resume=ResumeBundle(
            parsed=ParsedResume(
                skills=["python"],
                projects=[],
                experience=[],
                education=[],
                certifications=[],
                achievements=[],
                raw_text="mock text",
            ),
            analysis=ResumeAnalysis(
                summary="A test candidate", 
                gaps=[],
                strengths=[],
                ats_issues=[]
            ),
            graph=KnowledgeGraph(nodes=[], edges=[])
        ),
        plan=InterviewPlan(
            sections=[
                InterviewSection(
                    name="Core Python",
                    objective="Assess python skills",
                    target_topics=["python"],
                    target_difficulty=Difficulty.medium,
                    estimated_turns=5
                )
            ],
            total_estimated_turns=5,
            scoring_criteria=[]
        ),
        transcript=[
            TranscriptTurn(role="interviewer", content="Tell me about Python", topic="python")
        ],
        covered_topics=["python"],
        current_difficulty=Difficulty.medium,
        phase=InterviewPhase.IN_SECTION,
        turn_count=0
    )

@patch("app.services.interview_engine.llm.complete_json")
def test_next_question_regression(mock_complete_json, mock_state):
    # Setup mock to return a canned response simulating the LLM decision
    mock_complete_json.return_value = {
        "question": "What is the GIL?",
        "topic": "python_gil",
        "strategy": "deepen",
        "rationale": "Testing depth of knowledge"
    }
    
    # 1. Run the candidate's answer through the engine
    answer = "I know Python very well."
    response = next_question(mock_state, answer)
    
    # 2. Verify identical questions/strategies/difficulty progression 
    # as the legacy logic would have produced for a "deepen" strategy.
    
    # The transcript should now include the candidate's answer and the new question
    assert len(mock_state.transcript) == 3
    assert mock_state.transcript[-2].role == "candidate"
    assert mock_state.transcript[-2].content == answer
    assert mock_state.transcript[-1].role == "interviewer"
    assert mock_state.transcript[-1].content == "What is the GIL?"
    
    # Difficulty logic: 
    # Current = medium, section target = medium
    # Strategy "deepen" nudges UP toward target (but not exceeding target+1 step)
    # Wait, in the new adaptive_difficulty, if current(medium) < target(medium)+1 (which is hard), it nudges up to hard?
    # Let's see: target_idx is 1. target_idx + 1 is 2. current_idx is 1. 1 < 2, so it nudges up to 2 (hard).
    assert response.difficulty == Difficulty.hard
    assert mock_state.current_difficulty == Difficulty.hard
    
    # State should advance properly
    assert mock_state.turn_count == 1
    assert "python_gil" in mock_state.covered_topics
    
    # The response matches the generated structure
    assert response.question == "What is the GIL?"
    assert response.topic == "python_gil"
    assert response.section == "Core Python"
    assert response.rationale == "Testing depth of knowledge"
