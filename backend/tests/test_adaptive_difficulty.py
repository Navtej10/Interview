import pytest
from app.models.schemas import Difficulty, InterviewState, PerformanceNote, ResumeBundle, ParsedResume, ResumeAnalysis, KnowledgeGraph, InterviewPlan
from app.services.adaptive_difficulty import next_difficulty, should_consider_early_section_exit

@pytest.fixture
def mock_state():
    resume = ResumeBundle(
        parsed=ParsedResume(skills=[], projects=[], experience=[], education=[], certifications=[], achievements=[], raw_text=""),
        analysis=ResumeAnalysis(summary="", gaps=[], strengths=[], ats_issues=[]),
        graph=KnowledgeGraph(nodes=[], edges=[])
    )
    plan = InterviewPlan(sections=[], total_estimated_turns=0, scoring_criteria=[])
    return InterviewState(
        session_id="test",
        resume=resume,
        plan=plan,
        transcript=[],
        performance_notes=[],
        current_difficulty=Difficulty.medium,
        turn_count=0
    )

def test_next_difficulty_boundaries(mock_state):
    # Test "deepen" from already-hard stays at hard
    new_diff, early_exit = next_difficulty(Difficulty.hard, "deepen", Difficulty.hard, mock_state)
    assert new_diff == Difficulty.hard
    
    # Even if target is hard, we can't exceed hard.
    new_diff, early_exit = next_difficulty(Difficulty.hard, "deepen", Difficulty.medium, mock_state)
    assert new_diff == Difficulty.hard
    
    # Test "simplify" from already-easy stays at easy
    new_diff, early_exit = next_difficulty(Difficulty.easy, "simplify", Difficulty.easy, mock_state)
    assert new_diff == Difficulty.easy

def test_should_consider_early_section_exit(mock_state):
    # Initially False
    assert should_consider_early_section_exit(mock_state) is False
    
    # 2 poor notes at easy -> False (default n=3)
    mock_state.performance_notes.append(PerformanceNote(topic="t1", difficulty=Difficulty.easy, quality="poor"))
    mock_state.performance_notes.append(PerformanceNote(topic="t2", difficulty=Difficulty.easy, quality="poor"))
    assert should_consider_early_section_exit(mock_state) is False
    
    # 3 poor notes at easy -> True
    mock_state.performance_notes.append(PerformanceNote(topic="t3", difficulty=Difficulty.easy, quality="poor"))
    assert should_consider_early_section_exit(mock_state) is True
    
    # If one of them was not easy, it should be False
    mock_state.performance_notes[-1] = PerformanceNote(topic="t3", difficulty=Difficulty.medium, quality="poor")
    assert should_consider_early_section_exit(mock_state) is False
