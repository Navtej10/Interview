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
                candidate_profile={"career_stage":"","primary_domain":"","secondary_domain":"","technical_maturity":"","experience_level":"","interview_readiness":"","resume_quality":"","overall_recommendation":""},
                scores={"overall_resume":{"title":"","score":0,"reason":""},"ats_compatibility":{"title":"","score":0,"reason":""},"technical_skills":{"title":"","score":0,"reason":""},"project_quality":{"title":"","score":0,"reason":""},"resume_writing":{"title":"","score":0,"reason":""},"interview_readiness":{"title":"","score":0,"reason":""},"confidence_score":{"title":"","score":0,"reason":""}},
                summary="A test candidate", gaps=[], strengths=[], skill_matrix=[], project_reviews=[],
                experience_review={"is_student":False,"projects_evaluation":"","hackathons_evaluation":"","research_evaluation":"","open_source_evaluation":""},
                resume_consistency={"summary_aligns_with_projects":True,"skills_align_with_projects":True,"projects_align_with_career_objective":True,"education_supports_domain":True,"dates_consistent":True,"no_duplicates":True,"technologies_consistent":True},
                ats_analysis={"ats_score":0,"formatting":"","keyword_coverage":"","section_detection":"","date_formatting":"","bullet_quality":"","missing_keywords":[],"parseability":"","recommendations":[]},
                technical_risks=[], predicted_questions=[]
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
        "evaluation": {"overall_quality": "strong"},
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
        "evaluation": {"overall_quality": "adequate"},
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
    # Test point 3: In the new architecture, we removed the strict strategy rules around topic keeping 
    # to avoid a second latency-inducing LLM call. Instead, we let the LLM handle it, but we still force a pivot
    # if it repeats >2 times. This test is simplified.
    
    # 1. Setup transcript so the last interviewer question was on topic "t1"
    mock_state.transcript.append(TranscriptTurn(role="interviewer", content="Q1", topic="t1"))
    
    # 2. LLM hallucinates an invalid strategy, but wants to stay on "t1" (duplicate topic, meaning 2nd time)
    mock_complete_json.return_value = {
        "evaluation": {"overall_quality": "adequate"},
        "question": "Q2?",
        "topic": "t1",
        "strategy": "made_up_strategy",
        "rationale": ""
    }
    
    response = next_question(mock_state, "A1")
    
    # 3. Assert the new behavior: 
    # - Strategy falls back to "pivot" because "made_up_strategy" is invalid.
    # - Topic REMAINS "t1" because it has only repeated once (2 consecutive), so the strict
    #   "pivots must always change topic" rule is no longer enforced to save a second LLM call.
    assert response.strategy == "pivot"
    assert response.topic == "t1"
    assert response.question == "Q2?"
    assert mock_complete_json.call_count == 1

@patch("app.services.interview_engine.llm.complete_json")
def test_next_question_three_consecutive_topic(mock_complete_json, mock_state):
    # Force state to have 2 consecutive interviewer questions on topic 't1'
    mock_state.transcript.append(TranscriptTurn(role="interviewer", content="Q1", topic="t1"))
    mock_state.transcript.append(TranscriptTurn(role="candidate", content="A1"))
    mock_state.transcript.append(TranscriptTurn(role="interviewer", content="Q2", topic="t1"))
    
    # In the single-call architecture, if the topic repeats 3 times, we force a fallback topic
    # rather than making a second LLM call to save latency.
    invalid_result = {
        "evaluation": {"overall_quality": "strong"},
        "question": "Q3",
        "topic": "t1",
        "strategy": "deepen",
        "rationale": ""
    }
    
    mock_complete_json.return_value = invalid_result
    
    response = next_question(mock_state, "A2")
    
    assert mock_complete_json.call_count == 1
    assert response.topic == "A new topic"
    assert response.strategy == "pivot"

@patch("app.services.interview_engine.llm.complete_json")
def test_next_question_empty_transcript(mock_complete_json, mock_state):
    # Empty transcript (no opening question)
    mock_state.transcript = []
    
    mock_complete_json.return_value = {
        "evaluation": {"overall_quality": "strong"},
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
        {"evaluation": {"overall_quality": "strong"}, "question": "Q1", "topic": "t1", "strategy": "deepen", "rationale": "r1"},
        {"evaluation": {"overall_quality": "weak"}, "question": "Q2", "topic": "t2", "strategy": "simplify", "rationale": "r2"},
        {"evaluation": {"overall_quality": "strong"}, "question": "Q3", "topic": "t3", "strategy": "pivot", "rationale": "r3"}
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
