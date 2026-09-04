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
    Returns (section, section_index) based on state.current_section_index.
    Ensures index doesn't exceed bounds.
    """
    idx = min(state.current_section_index, len(state.plan.sections) - 1)
    return state.plan.sections[idx], idx

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

    if has_exceeded_plan(state) or state.termination_reason is not None:
        return InterviewPhase.closing
        
    _, current_idx = current_section(state)
    
    if current_idx == 0:
        return InterviewPhase.introduction
    elif current_idx == 1:
        return InterviewPhase.background
    elif current_idx == 2:
        return InterviewPhase.technical
    elif current_idx == 3:
        return InterviewPhase.behavioral
    else:
        return InterviewPhase.closing
