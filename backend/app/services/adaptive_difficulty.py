"""
Module for adaptively nudging the difficulty of the interview purely deterministically.
"""

from app.models.schemas import Difficulty, InterviewState

_DIFFICULTY_ORDER = [Difficulty.easy, Difficulty.medium, Difficulty.hard]

def should_consider_early_section_exit(state: InterviewState, n: int = 3) -> bool:
    """
    Surfaces a signal if the candidate has sustained struggle on the easiest difficulty.
    If we've dropped to 'easy' and still get 'simplify' (recorded as 'poor' quality)
    for N consecutive turns, we should probably exit the section early rather than
    keeping them stuck at 'easy' indefinitely.
    """
    if len(state.performance_notes) < n:
        return False
        
    recent_notes = state.performance_notes[-n:]
    return all(note.quality == "poor" and note.difficulty == Difficulty.easy for note in recent_notes)

def next_difficulty(current: Difficulty, strategy: str, section_target: Difficulty, state: InterviewState) -> tuple[Difficulty, bool]:
    """
    Determines the next difficulty level based on the chosen strategy and section target.
    Returns a tuple of (new_difficulty, consider_early_section_exit).
    """
    current_idx = _DIFFICULTY_ORDER.index(current)
    target_idx = _DIFFICULTY_ORDER.index(section_target)
    
    new_idx = current_idx
    
    if strategy == "deepen":
        # Nudge up toward target, but do not exceed target by more than 1 step
        if current_idx < target_idx + 1:
            new_idx += 1
    elif strategy == "simplify":
        # Nudge down one step but never below "easy"
        if current_idx > 0:
            new_idx -= 1
    # "pivot" and "follow_up_tangent" hold difficulty steady

    # Enforce bounds
    new_idx = max(0, min(len(_DIFFICULTY_ORDER) - 1, new_idx))
    new_diff = _DIFFICULTY_ORDER[new_idx]
    
    # Check early exit condition using our new function
    consider_early_exit = should_consider_early_section_exit(state)

    return new_diff, consider_early_exit

def quality_from_strategy(strategy: str) -> str:
    """
    Derives a rough quality signal for the PerformanceNote strictly from the 
    engine's chosen conversational strategy.
    
    Note: This is a deliberate simplification. It maps the chosen strategy 
    directly to a performance quality, conflating "the strategy chosen" with 
    "how well the candidate actually did". While usually correlated, they aren't 
    identical (e.g. pivoting after an excellent answer). We accept this tradeoff
    to keep the pipeline entirely deterministic without needing to parse the
    unstructured LLM `rationale` field.
    """
    if strategy == "deepen":
        return "good"
    elif strategy == "simplify":
        return "poor"
    return "neutral"
