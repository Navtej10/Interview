import pytest
from app.models.schemas import (
    InterviewState, TranscriptTurn, Difficulty, PerformanceNote,
    ResumeBundle, ParsedResume, ResumeAnalysis, KnowledgeGraph,
    InterviewPlan, InterviewSection, InterviewPhase
)
from app.services.memory import build_context, record_performance
from app.config import settings

@pytest.fixture
def mock_state():
    return InterviewState(
        session_id="test_session",
        resume=ResumeBundle(
            parsed=ParsedResume(skills=[], projects=[], experience=[], education=[], certifications=[], achievements=[], raw_text=""),
            analysis=ResumeAnalysis(summary="", gaps=[], strengths=[], ats_issues=[]),
            graph=KnowledgeGraph(nodes=[], edges=[])
        ),
        plan=InterviewPlan(sections=[], total_estimated_turns=0, scoring_criteria=[]),
        transcript=[],
        covered_topics=[],
        performance_notes=[],
        current_difficulty=Difficulty.medium,
        turn_count=0
    )


def test_build_context_and_record_performance(mock_state):
    original_window = settings.short_term_window
    settings.short_term_window = 2
    
    # Simulate a conversation with 3 full turns (6 items in transcript)
    for i in range(1, 4):
        topic = f"topic{i}"
        mock_state.transcript.append(TranscriptTurn(role="interviewer", content=f"Q{i}"))
        mock_state.transcript.append(TranscriptTurn(role="candidate", content=f"A{i}"))
        
        # Engine calls record_performance
        record_performance(mock_state, topic, Difficulty.medium, "good")
        
    # Transcript has 6 items. The window is 2, so only the last 2 items (Q3, A3) should be short_term.
    short_term_text, long_term_text = build_context(mock_state)
    
    # Assert short term text only has the last 2 items
    assert "Q3" in short_term_text
    assert "A3" in short_term_text
    assert "Q1" not in short_term_text
    assert "Q2" not in short_term_text
    
    # Assert long term text has the performance notes
    assert "topic1" in long_term_text
    assert "topic2" in long_term_text
    assert "topic3" in long_term_text
    assert "Diff: medium" in long_term_text
    assert "Quality: good" in long_term_text
    
    # Restore window
    settings.short_term_window = original_window
