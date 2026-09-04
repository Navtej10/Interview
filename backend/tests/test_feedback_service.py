import pytest
from unittest.mock import patch
from app.models.schemas import (
    InterviewState, ResumeBundle, ParsedResume, ResumeAnalysis, 
    KnowledgeGraph, InterviewPlan, InterviewSection, ScoringCriterion, Difficulty,
    InterviewPhase, TranscriptTurn, ScoringResult, CriterionScore, TerminationReason
)
from app.services.feedback_service import generate_written_report

@pytest.fixture
def mock_state():
    return InterviewState(
        session_id="test_session",
        resume=ResumeBundle(
            parsed=ParsedResume(
                skills=["python"], projects=[], experience=[], education=[], certifications=[], achievements=[], raw_text="mock text"
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
        is_complete=True,
        final_scores=ScoringResult(
            scores=[CriterionScore(criterion_name="Technical Depth", score=0.8, justification="Good", location="")],
            weighted_overall=0.8
        )
    )

@patch("app.services.feedback_service.llm.complete_json")
def test_generate_report_strong_candidate(mock_complete_json, mock_state):
    # Mock LLM returning the full new schema
    mock_complete_json.return_value = {
        "overall_performance": {"summary": "Great", "completion_status": "Complete", "strongest_areas": ["Python"], "weakest_areas": []},
        "technical_knowledge": {"technical_correctness": "High", "depth_of_understanding": "Deep", "implementation_details": "Clear", "fundamentals": "Strong", "tradeoffs": "Good", "debugging_problem_solving": "Good", "system_design": "Good"},
        "communication": {"clarity": "Clear", "structure": "Good", "conciseness": "Good", "directness": "Good", "explanation_ability": "Good", "concrete_examples": "Used"},
        "reasoning_ability": {"problem_breakdown": "Good", "explaining_reasoning": "Good", "evaluating_alternatives": "Good", "reasoning_tradeoffs": "Good", "handling_followups": "Good", "adaptability": "Good"},
        "project_ownership": {"what_built": "App", "responsibilities": "Dev", "technical_decisions": "Good", "challenges": "Handled", "outcomes": "Good"},
        "resume_credibility": {"supported_claims": ["Python"], "partially_supported_claims": [], "unverified_claims": [], "inconsistencies": []},
        "technical_weaknesses": [],
        "communication_weaknesses": [],
        "interview_behavior": {"patterns": ["Engaged"]},
        "confidence_levels": {"high_confidence": ["Python"], "medium_confidence": [], "low_confidence": [], "unassessed": []},
        "early_termination_context": None
    }
    
    report = generate_written_report(mock_state)
    assert report.overall_performance.summary == "Great"
    assert "Python" in report.resume_credibility.supported_claims

@patch("app.services.feedback_service.llm.complete_json")
def test_generate_report_early_termination(mock_complete_json, mock_state):
    mock_state.termination_reason = TerminationReason.early_insufficient_evidence
    mock_complete_json.return_value = {
        "overall_performance": {"summary": "Ended early", "completion_status": "Early Termination", "strongest_areas": [], "weakest_areas": []},
        "technical_knowledge": {"technical_correctness": "", "depth_of_understanding": "", "implementation_details": "", "fundamentals": "", "tradeoffs": "", "debugging_problem_solving": "", "system_design": ""},
        "communication": {"clarity": "", "structure": "", "conciseness": "", "directness": "", "explanation_ability": "", "concrete_examples": ""},
        "reasoning_ability": {"problem_breakdown": "", "explaining_reasoning": "", "evaluating_alternatives": "", "reasoning_tradeoffs": "", "handling_followups": "", "adaptability": ""},
        "project_ownership": {"what_built": "", "responsibilities": "", "technical_decisions": "", "challenges": "", "outcomes": ""},
        "resume_credibility": {"supported_claims": [], "partially_supported_claims": [], "unverified_claims": ["Python"], "inconsistencies": []},
        "technical_weaknesses": [],
        "communication_weaknesses": [],
        "interview_behavior": {"patterns": ["Evasive"]},
        "confidence_levels": {"high_confidence": [], "medium_confidence": [], "low_confidence": [], "unassessed": ["Python"]},
        "early_termination_context": {
            "termination_reason": "early_insufficient_evidence",
            "meaningful_answers_collected": 1,
            "unassessed_dimensions": ["Technical Depth"],
            "assessment_reliability": "Low"
        }
    }
    
    report = generate_written_report(mock_state)
    assert report.early_termination_context is not None
    assert report.early_termination_context.termination_reason == "early_insufficient_evidence"
    assert "Python" in report.confidence_levels.unassessed

