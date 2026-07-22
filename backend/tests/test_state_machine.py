import pytest
from app.models.schemas import InterviewState, InterviewPlan, InterviewSection, Difficulty, ResumeBundle, ParsedResume, ResumeAnalysis, KnowledgeGraph
from app.services.state_machine import current_section, has_exceeded_plan, get_current_phase
from app.models.schemas import InterviewPhase

@pytest.fixture
def plan():
    return InterviewPlan(
        sections=[
            InterviewSection(name="Section 1", objective="1", target_topics=["1"], target_difficulty=Difficulty.medium, estimated_turns=2),
            InterviewSection(name="Section 2", objective="2", target_topics=["2"], target_difficulty=Difficulty.medium, estimated_turns=3)
        ],
        total_estimated_turns=5,
        scoring_criteria=[]
    )

@pytest.fixture
def mock_state(plan):
    resume = ResumeBundle(
        parsed=ParsedResume(skills=[], projects=[], experience=[], education=[], certifications=[], achievements=[], raw_text=""),
        analysis=ResumeAnalysis(summary="", gaps=[], strengths=[], ats_issues=[]),
        graph=KnowledgeGraph(nodes=[], edges=[])
    )
    return InterviewState(
        session_id="test",
        resume=resume,
        plan=plan,
        transcript=[],
        turn_count=0
    )

def test_current_section_fresh_interview(mock_state, plan):
    # Test that a fresh interview (turn_count=0, transcript=[]) returns section 0
    section, idx = current_section(mock_state)
    assert idx == 0
    assert section.name == "Section 1"
    
def test_current_section_after_opening(mock_state, plan):
    # After one turn (turn_count=0, but transcript has opening Q)
    # The question_index is 1, but section_index is still 0 (Section 1 has 2 turns)
    mock_state.transcript.append("Opening Q")
    section, idx = current_section(mock_state)
    assert idx == 0
    assert section.name == "Section 1"

def test_has_exceeded_plan_boundary(mock_state):
    # total_estimated_turns is 5
    # Should flip exactly at 5
    
    mock_state.turn_count = 4
    assert has_exceeded_plan(mock_state) is False
    
    mock_state.turn_count = 5
    assert has_exceeded_plan(mock_state) is True
    
    mock_state.turn_count = 6
    assert has_exceeded_plan(mock_state) is True

def test_get_current_phase(mock_state):
    mock_state.turn_count = 0
    assert get_current_phase(mock_state) == InterviewPhase.in_progress
    
    # 4 turns (0-3 is section 1 & part of section 2). Wait: Section 1 is 2 turns.
    # So turn 0, 1 -> section 1
    # turn 2, 3, 4 -> section 2
    
    # Let's test final_section. At turn_count=4, transcript not empty, next is 5.
    mock_state.transcript.append("dummy")
    mock_state.turn_count = 3
    assert get_current_phase(mock_state) == InterviewPhase.final_section
    
    mock_state.turn_count = 5
    assert get_current_phase(mock_state) == InterviewPhase.wrapping_up
    
    mock_state.is_complete = True
    assert get_current_phase(mock_state) == InterviewPhase.complete
