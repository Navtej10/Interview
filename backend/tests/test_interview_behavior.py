import pytest
from unittest.mock import patch

from app.services import orchestrator
from app.models.schemas import (
    ResumeBundle, ParsedResume, ResumeAnalysis, KnowledgeGraph,
    InterviewPlan, InterviewSection, Difficulty, AnswerEvaluation, AnswerQuality, TerminationReason, FeedbackReport
)
from app.services.state_machine import get_current_phase, InterviewPhase

@pytest.fixture
def mock_resume():
    parsed = ParsedResume(skills=["python"], projects=[], experience=[], education=[], certifications=[], achievements=[], raw_text="mock")
    analysis = ResumeAnalysis(
                candidate_profile={"career_stage":"","primary_domain":"","secondary_domain":"","technical_maturity":"","experience_level":"","interview_readiness":"","resume_quality":"","overall_recommendation":""},
                scores={"overall_resume":{"title":"","score":0,"reason":""},"ats_compatibility":{"title":"","score":0,"reason":""},"technical_skills":{"title":"","score":0,"reason":""},"project_quality":{"title":"","score":0,"reason":""},"resume_writing":{"title":"","score":0,"reason":""},"interview_readiness":{"title":"","score":0,"reason":""},"confidence_score":{"title":"","score":0,"reason":""}},
                summary="A test candidate", gaps=[], strengths=[], skill_matrix=[], project_reviews=[],
                experience_review={"is_student":False,"projects_evaluation":"","hackathons_evaluation":"","research_evaluation":"","open_source_evaluation":""},
                resume_consistency={"summary_aligns_with_projects":True,"skills_align_with_projects":True,"projects_align_with_career_objective":True,"education_supports_domain":True,"dates_consistent":True,"no_duplicates":True,"technologies_consistent":True},
                ats_analysis={"ats_score":0,"formatting":"","keyword_coverage":"","section_detection":"","date_formatting":"","bullet_quality":"","missing_keywords":[],"parseability":"","recommendations":[]},
                technical_risks=[], predicted_questions=[]
            )
    graph = KnowledgeGraph(nodes=[], edges=[])
    return ResumeBundle(parsed=parsed, analysis=analysis, graph=graph)

def start_test_interview(mock_resume):
    with patch("app.services.llm_client.llm.complete_json") as mock_complete:
        mock_complete.side_effect = [
            # Planner
            {
                "sections": [
                    {"name": "Intro", "objective": "Warmup", "target_topics": ["intro"], "target_difficulty": "easy", "estimated_turns": 1},
                    {"name": "Tech", "objective": "Tech", "target_topics": ["python"], "target_difficulty": "medium", "estimated_turns": 2},
                    {"name": "Deep Tech", "objective": "Deep", "target_topics": ["python"], "target_difficulty": "hard", "estimated_turns": 1},
                    {"name": "Wrap", "objective": "Wrap", "target_topics": [], "target_difficulty": "easy", "estimated_turns": 1}
                ],
                "total_estimated_turns": 5,
                "scoring_criteria": [{"name": "Technical", "weight": 1.0, "description": "Tech skills"}]
            },
            # Question Generator
            {
                "question": "Opening Q?",
                "topic": "intro",
                "rationale": "start",
                "strategy": "transition"
            }
        ]
        session_id, q, t, s, plan, r = orchestrator.start_interview(mock_resume)
        return session_id

def create_eval(quality: AnswerQuality, is_filler=False, is_evasive=False) -> AnswerEvaluation:
    return AnswerEvaluation(
        overall_quality=quality,
        relevance=1.0, technical_correctness=1.0, technical_depth=1.0, specificity=1.0, communication=1.0, reasoning=1.0, completeness=1.0,
        is_filler=is_filler, is_evasive=is_evasive, evidence=[], missing_points=[], strengths=[], concerns=[], confidence=1.0
    )

@patch("app.services.llm_client.llm.complete_json")
def test_scenario_1_strong_candidate(mock_complete_json, mock_resume):
    session_id = start_test_interview(mock_resume)
    
    # 5 turns of strong answers
    mock_complete_json.side_effect = [
        {"evaluation": {"overall_quality": "strong"}, "strategy": "transition", "topic": "t1", "question": "Q2", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "increase"},
        {"evaluation": {"overall_quality": "strong"}, "strategy": "deepen", "topic": "t2", "question": "Q3", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "increase"},
        {"evaluation": {"overall_quality": "strong"}, "strategy": "deepen", "topic": "t3", "question": "Q4", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "stable"},
        {"evaluation": {"overall_quality": "strong"}, "strategy": "transition", "topic": "t4", "question": "Q5", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "stable"},
        {"evaluation": {"overall_quality": "strong"}, "strategy": "transition", "topic": "wrap", "question": "done", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "stable"}
    ]
    
    for i in range(5):
        orchestrator.submit_answer(session_id, "Good answer")
    
    orchestrator.end_interview(session_id)
    
    state = orchestrator.session_store.get(session_id)
    assert state.turn_count == 5
    assert state.is_complete == True
    assert state.termination_reason == TerminationReason.normal_completion
    # Reached hard difficulty
    assert any(note.difficulty == Difficulty.hard for note in state.performance_notes)

@patch("app.services.llm_client.llm.complete_json")
def test_scenario_10_topic_exhaustion(mock_complete_json, mock_resume):
    session_id = start_test_interview(mock_resume)
    
    # Alternate adequate and weak
    mock_complete_json.side_effect = [
        {"evaluation": {"overall_quality": "adequate"}, "strategy": "transition", "topic": "t1", "question": "Q2", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "stable"},
    ]

@patch("app.services.llm_client.llm.complete_json")
def test_scenario_2_average_candidate(mock_complete_json, mock_resume):
    session_id = start_test_interview(mock_resume)
    
    # Alternate adequate and weak
    mock_complete_json.side_effect = [
        {"evaluation": {"overall_quality": "adequate"}, "strategy": "transition", "topic": "t1", "question": "Q2", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "stable"},
        {"evaluation": {"overall_quality": "weak"}, "strategy": "simplify", "topic": "t2", "question": "Q3", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "decrease"},
        {"evaluation": {"overall_quality": "adequate"}, "strategy": "pivot", "topic": "t3", "question": "Q4", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "stable"},
        {"evaluation": {"overall_quality": "weak"}, "strategy": "simplify", "topic": "t4", "question": "Q5", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "decrease"},
        {"evaluation": {"overall_quality": "adequate"}, "strategy": "transition", "topic": "wrap", "question": "done", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "stable"}
    ]
    
    for i in range(5):
        orchestrator.submit_answer(session_id, "Average answer")
    
    orchestrator.end_interview(session_id)
    
    state = orchestrator.session_store.get(session_id)
    assert state.termination_reason == TerminationReason.normal_completion
    assert state.is_complete == True

@patch("app.services.llm_client.llm.complete_json")
def test_scenario_3_weak_candidate_early_termination(mock_complete_json, mock_resume):
    session_id = start_test_interview(mock_resume)
    
    # 4 consecutive weak answers
    mock_complete_json.side_effect = [
        {"evaluation": {"overall_quality": "weak"}, "strategy": "simplify", "topic": f"t{i}", "question": "Q2", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "decrease"}
        for i in range(4)
    ]
    
    # Turn 1
    orchestrator.submit_answer(session_id, "Weak")
    state = orchestrator.session_store.get(session_id)
    assert state.current_difficulty == Difficulty.easy
    
    # Turn 2
    orchestrator.submit_answer(session_id, "Weak")
    
    # Turn 3
    orchestrator.submit_answer(session_id, "Weak")
    state = orchestrator.session_store.get(session_id)
    # 3 consecutive weak triggers early_insufficient_evidence
    assert state.termination_reason == TerminationReason.early_insufficient_evidence
    assert get_current_phase(state) == InterviewPhase.wrapping_up

@patch("app.services.llm_client.llm.complete_json")
def test_scenario_4_garbage_filler_candidate(mock_complete_json, mock_resume):
    session_id = start_test_interview(mock_resume)
    
    # Garbage/filler
    mock_complete_json.side_effect = [
        {"evaluation": {"overall_quality": "filler", "is_filler": True}, "strategy": "simplify", "topic": "t1", "question": "Q", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "decrease"},
        {"evaluation": {"overall_quality": "evasive", "is_evasive": True}, "strategy": "simplify", "topic": "t2", "question": "Q", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "decrease"},
        {"evaluation": {"overall_quality": "filler", "is_filler": True}, "strategy": "simplify", "topic": "t3", "question": "Q", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "decrease"}
    ]
    
    orchestrator.submit_answer(session_id, "Yes")
    orchestrator.submit_answer(session_id, "Basically we used AI")
    orchestrator.submit_answer(session_id, "It was a good project")
    
    state = orchestrator.session_store.get(session_id)
    assert state.termination_reason == TerminationReason.early_repeated_non_answers

@patch("app.services.llm_client.llm.complete_json")
def test_scenario_5_one_bad_answer_then_recovery(mock_complete_json, mock_resume):
    session_id = start_test_interview(mock_resume)
    
    mock_complete_json.side_effect = [
        {"evaluation": {"overall_quality": "weak"}, "strategy": "simplify", "topic": "t1", "question": "Q", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "decrease"},
        {"evaluation": {"overall_quality": "excellent"}, "strategy": "deepen", "topic": "t2", "question": "Q", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "increase"},
        {"evaluation": {"overall_quality": "excellent"}, "strategy": "deepen", "topic": "t3", "question": "Q", "rationale": "r", "relationship_to_answer": "r", "difficulty_adjustment": "increase"}
    ]
    
    orchestrator.submit_answer(session_id, "bad")
    state = orchestrator.session_store.get(session_id)
    assert state.current_difficulty == Difficulty.easy
    
    orchestrator.submit_answer(session_id, "great")
    orchestrator.submit_answer(session_id, "great")
    state = orchestrator.session_store.get(session_id)
    
    assert state.termination_reason is None
