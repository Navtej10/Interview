"""
State machine for governing valid transitions in the interview process.
"""

from app.models.schemas import InterviewState, InterviewPhase
from app.services.planner import section_for_question_index


def advance(state: InterviewState) -> InterviewState:
    """
    Evaluates the current state and advances the InterviewPhase accordingly.
    This reads from state.turn_count and section constraints.
    Returns the mutated state for convenience.
    """
    if state.is_complete:
        state.phase = InterviewPhase.COMPLETE
        return state

    if state.phase == InterviewPhase.NOT_STARTED:
        # Before any turns, if the interview hasn't started
        pass

    # Question about to be generated is at index `state.turn_count + 1`.
    # Turn count 0 means 1 question has been asked (the opening question).
    
    if state.turn_count >= state.plan.total_estimated_turns:
        state.phase = InterviewPhase.WRAPPING_UP
        return state

    # We need to look ahead to see if the NEXT question (after the one we are about to generate)
    # is in a new section, which means the question we are about to generate is the LAST in its section.
    # Actually, we want to know if the question about to be asked is the last one in the section.
    
    current_section, current_idx = section_for_question_index(state.plan, state.turn_count + 1)
    next_section, next_idx = section_for_question_index(state.plan, state.turn_count + 2)

    if current_idx != next_idx:
        state.phase = InterviewPhase.TRANSITIONING_SECTION
    else:
        state.phase = InterviewPhase.IN_SECTION

    return state
