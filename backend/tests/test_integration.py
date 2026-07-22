import pytest
from unittest.mock import patch, MagicMock

from app.services import orchestrator
from app.models.schemas import (
    ResumeBundle, ParsedResume, ResumeAnalysis, KnowledgeGraph,
    InterviewPlan, InterviewSection, Difficulty, FeedbackReport
)

@pytest.fixture
def mock_resume_bytes():
    return b"dummy resume content"

@patch("app.services.orchestrator.parse_resume")
@patch("app.services.orchestrator.build_graph")
@patch("app.services.orchestrator.analyze")
@patch("app.services.llm_client.llm.complete_json")
def test_full_interview_lifecycle(
    mock_complete_json,
    mock_analyze,
    mock_build_graph,
    mock_parse,
    mock_resume_bytes
):
    # 1. Mock setup
    parsed = ParsedResume(skills=["python"], projects=[], experience=[], education=[], certifications=[], achievements=[], raw_text="mock")
    analysis = ResumeAnalysis(summary="Good", gaps=[], strengths=[], ats_issues=[])
    graph = KnowledgeGraph(nodes=[], edges=[])
    
    mock_parse.return_value = parsed
    mock_build_graph.return_value = graph
    mock_analyze.return_value = analysis
    
    mock_complete_json.side_effect = [
        # 1. Planner
        {
            "sections": [
                {"name": "Intro", "objective": "Warmup", "target_topics": ["python"], "target_difficulty": "easy", "estimated_turns": 2}
            ],
            "scoring_criteria": [
                {"name": "Technical", "weight": 1.0, "description": "Tech skills"}
            ]
        },
        # 2. Question Generator
        {
            "question": "Opening Q?",
            "topic": "intro",
            "rationale": "start"
        },
        # 3. Interview Engine (Turn 1)
        {"question": "Q2?", "topic": "t2", "strategy": "deepen", "rationale": "r2"},
        # 4. Interview Engine (Turn 2)
        {"question": "Q3?", "topic": "t3", "strategy": "pivot", "rationale": "r3"},
        # 5. Feedback Service - Score Interview
        {
            "scores": [{"criterion_name": "Technical", "score": 8.0, "justification": "Good", "location": "Turn 1"}]
        },
        # 6. Feedback Service - Generate Written Report
        {
            "overall_summary": "Solid candidate.",
            "moment_highlights": ["Knows python"],
            "recommended_next_steps": ["Hire"],
            "strengths": ["Knows python"],
            "weaknesses": []
        },
        # 7. Fallback in case of retry
        {
            "overall_summary": "Solid candidate.",
            "moment_highlights": ["Knows python"],
            "recommended_next_steps": ["Hire"],
            "strengths": ["Knows python"],
            "weaknesses": []
        }
    ]

    # 2. Execution
    # analyze_resume
    resume_bundle = orchestrator.analyze_resume(mock_resume_bytes, "resume.pdf")
    assert resume_bundle.parsed.skills == ["python"]
    
    # start_interview
    session_id, q, t, s, plan, r = orchestrator.start_interview(resume_bundle)
    assert q == "Opening Q?"
    assert session_id is not None
    
    # process_turn x2 (submit_answer in orchestrator)
    res1 = orchestrator.submit_answer(session_id, "Answer 1")
    assert res1.question == "Q2?"
    
    res2 = orchestrator.submit_answer(session_id, "Answer 2")
    assert res2.question == "Q3?"
    
    # end_interview
    end_res = orchestrator.end_interview(session_id)
    assert end_res["session_id"] == session_id
    assert end_res["turn_count"] == 2
    
    # get_written_report
    report = orchestrator.get_written_report(session_id)
    assert isinstance(report, FeedbackReport)
    assert report.overall_summary == "Solid candidate."
    assert len(report.scores) == 1
