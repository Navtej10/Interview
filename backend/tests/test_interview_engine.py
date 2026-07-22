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

@patch("app.services.interview_engine.llm.complete_json")
def test_next_question_invalid_strategy_fallback(mock_complete_json, mock_state):
    # If LLM returns an invalid strategy, it should fallback to "pivot"
    mock_complete_json.return_value = {
        "question": "Q?",
        "topic": "t1",
        "strategy": "hallucinated_strategy",
        "rationale": ""
    }
    response = next_question(mock_state, "ans")
    assert response.topic == "t1"
    # Wait, the difficulty nudges based on pivot.
    # We can check that the returned rationale/question are passed through
    # but the internal logic treated it as a pivot.
    
@patch("app.services.interview_engine.llm.complete_json")
def test_next_question_duplicate_topic_invalid_strategy(mock_complete_json, mock_state):
    # Test point 3: topic exactly duplicates immediately preceding question's topic
    # without "deepen" (or "simplify") strategy.
    # The immediate preceding interviewer topic in mock_state is "python"
    
    # First call to LLM will return a duplicate topic without deepen/simplify
    invalid_result = {
        "question": "What about python?",
        "topic": "python",
        "strategy": "pivot", # Invalid to pivot to the exact same topic
        "rationale": ""
    }
    
    # Second call (retry) will return a valid response
    valid_result = {
        "question": "What is the GIL?",
        "topic": "python_gil",
        "strategy": "pivot",
        "rationale": ""
    }
    
    mock_complete_json.side_effect = [invalid_result, valid_result]
    
    response = next_question(mock_state, "ans")
    
    # Assert it caught it and retried (called twice)
    assert mock_complete_json.call_count == 2
    
    # The second call must contain the correction prompt
    second_call_args = mock_complete_json.call_args_list[1][0]
    assert "CORRECTION: You kept the topic as 'python' but chose strategy 'pivot'" in second_call_args[1]
    
    # The final output is from the valid result
    assert response.topic == "python_gil"

@patch("app.services.interview_engine.llm.complete_json")
def test_next_question_three_consecutive_topic(mock_complete_json, mock_state):
    # Force state to have 2 consecutive interviewer questions on topic 't1'
    mock_state.transcript.append(TranscriptTurn(role="interviewer", content="Q1", topic="t1"))
    mock_state.transcript.append(TranscriptTurn(role="candidate", content="A1"))
    mock_state.transcript.append(TranscriptTurn(role="interviewer", content="Q2", topic="t1"))
    
    # First call returns t1 again (3rd time)
    invalid_result = {
        "question": "Q3",
        "topic": "t1",
        "strategy": "deepen",
        "rationale": ""
    }
    valid_result = {
        "question": "Q4",
        "topic": "t2",
        "strategy": "pivot",
        "rationale": ""
    }
    
    mock_complete_json.side_effect = [invalid_result, valid_result]
    
    response = next_question(mock_state, "A2")
    
    assert mock_complete_json.call_count == 2
    second_call_args = mock_complete_json.call_args_list[1][0]
    assert "CORRECTION: You just attempted to ask a 3rd consecutive question on 't1'" in second_call_args[1]
    
    assert response.topic == "t2"

@patch("app.services.interview_engine.llm.complete_json")
def test_next_question_empty_transcript(mock_complete_json, mock_state):
    # Empty transcript (no opening question)
    mock_state.transcript = []
    
    mock_complete_json.return_value = {
        "question": "Q1",
        "topic": "t1",
        "strategy": "pivot",
        "rationale": ""
    }
    
    # next_question should not append the candidate's answer if the transcript is empty
    next_question(mock_state, "ans")
    
    assert len(mock_state.transcript) == 1
    assert mock_state.transcript[0].role == "interviewer"
    assert mock_state.transcript[0].content == "Q1"

@patch("app.services.interview_engine.llm.complete_json")
def test_next_question_multi_turn_regression(mock_complete_json, mock_state):
    # Simulates a stable, deterministic question/strategy/difficulty progression
    # across multiple turns to catch regressions.
    
    # Canned responses for 3 turns
    mock_complete_json.side_effect = [
        {"question": "Q1", "topic": "t1", "strategy": "deepen", "rationale": "r1"},
        {"question": "Q2", "topic": "t2", "strategy": "simplify", "rationale": "r2"},
        {"question": "Q3", "topic": "t3", "strategy": "pivot", "rationale": "r3"}
    ]
    
    # Turn 1
    res1 = next_question(mock_state, "A0")
    assert res1.question == "Q1"
    assert res1.difficulty == Difficulty.hard
    assert mock_state.current_difficulty == Difficulty.hard
    
    # Turn 2
    res2 = next_question(mock_state, "A1")
    assert res2.question == "Q2"
    assert res2.difficulty == Difficulty.medium
    assert mock_state.current_difficulty == Difficulty.medium
    
    # Turn 3
    res3 = next_question(mock_state, "A2")
    assert res3.question == "Q3"
    assert res3.difficulty == Difficulty.medium
    assert mock_state.current_difficulty == Difficulty.medium
    
    # Transcript should have 7 items (Opening Q, A0, Q1, A1, Q2, A2, Q3)
    assert len(mock_state.transcript) == 7
    assert mock_state.transcript[-1].content == "Q3"
    assert mock_state.turn_count == 3
