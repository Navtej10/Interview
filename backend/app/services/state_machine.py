"""
State machine for governing valid transitions in the interview process.

Design Rationale:
- Phase is derived purely from turn_count and the plan, rather than stored
  separately, avoiding duplicated, driftable state.
- We do not persist current_section_index on InterviewState for the same reason.
- This module is LLM-free and purely deterministic.
"""

from app.models.schemas import InterviewState, InterviewPhase
from app.services.planner import section_for_question_index

def current_section(state: InterviewState):
    """
    Returns (section, section_index) for the upcoming question.
    Computes question_index as turn_count + 1 only if there's an existing transcript,
    otherwise returns the opening section (index 0).
    """
    if state.transcript:
        idx = state.turn_count + 1
    else:
        idx = 0
    return section_for_question_index(state.plan, idx)

def has_exceeded_plan(state: InterviewState) -> bool:
    """
    Returns True exactly when the interview has met or exceeded the planned 
    total estimated turns.
    """
    return state.turn_count >= state.plan.total_estimated_turns

def get_current_phase(state: InterviewState) -> InterviewPhase:
    """
    Derives the current interview phase purely from the state and plan.
    """
    if state.is_complete:
        return InterviewPhase.complete

    if has_exceeded_plan(state):
        return InterviewPhase.wrapping_up
        
    _, current_idx = current_section(state)
    
    if current_idx == len(state.plan.sections) - 1:
        return InterviewPhase.final_section

    return InterviewPhase.in_progress
