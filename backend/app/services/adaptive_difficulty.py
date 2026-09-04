"""
Module for adaptively nudging the difficulty of the interview purely deterministically.
"""

from app.models.schemas import Difficulty, InterviewState, AnswerEvaluation, AnswerQuality

_DIFFICULTY_ORDER = [Difficulty.easy, Difficulty.medium, Difficulty.hard]

def should_consider_early_section_exit(state: InterviewState, n: int = 3) -> bool:
    """
    Surfaces a signal if the candidate has sustained struggle on the easiest difficulty.
    If we've dropped to 'easy' and still get weak/incorrect/filler/evasive quality
    for N consecutive turns, we should probably exit the section early rather than
    keeping them stuck at 'easy' indefinitely.
    """
    if len(state.performance_notes) < n:
        return False
        
    recent_notes = state.performance_notes[-n:]
    poor_qualities = {
        AnswerQuality.weak, 
        AnswerQuality.irrelevant, 
        AnswerQuality.filler, 
        AnswerQuality.evasive, 
        AnswerQuality.incorrect, 
        AnswerQuality.no_answer
    }
    return all(note.evaluation.overall_quality in poor_qualities and note.difficulty == Difficulty.easy for note in recent_notes)

def next_difficulty(current: Difficulty, evaluation: AnswerEvaluation, section_target: Difficulty, state: InterviewState) -> tuple[Difficulty, bool]:
    """
    Determines the next difficulty level based on the explicit evaluation and section target.
    Returns a tuple of (new_difficulty, consider_early_section_exit).
    """
    current_idx = _DIFFICULTY_ORDER.index(current)
    target_idx = _DIFFICULTY_ORDER.index(section_target)
    
    new_idx = current_idx
    quality = evaluation.overall_quality
    
    notes = state.performance_notes
    
    # Check if we recently dropped difficulty (to prevent bouncing right back up)
    recently_dropped = False
    if len(notes) >= 2:
        prev_diff_idx = _DIFFICULTY_ORDER.index(notes[-1].difficulty)
        older_diff_idx = _DIFFICULTY_ORDER.index(notes[-2].difficulty)
        if prev_diff_idx < older_diff_idx:
            recently_dropped = True

    if quality in (AnswerQuality.excellent, AnswerQuality.strong):
        # Nudge up toward target, but do not exceed target by more than 1 step
        # Anti-oscillation: If we recently dropped difficulty, hold steady for one turn to confirm stability
        if current_idx < target_idx + 1 and not recently_dropped:
            new_idx += 1
    elif quality in (AnswerQuality.weak, AnswerQuality.incorrect, AnswerQuality.no_answer):
        # Nudge down one step but never below "easy"
        if current_idx > 0:
            new_idx -= 1
    # For "adequate", "partial", "filler", "evasive", "irrelevant", we hold difficulty steady
    # and rely on the strategy engine to decide if we probe further or move on.

    # Enforce bounds
    new_idx = max(0, min(len(_DIFFICULTY_ORDER) - 1, new_idx))
    new_diff = _DIFFICULTY_ORDER[new_idx]
    
    # Check early exit condition
    consider_early_exit = should_consider_early_section_exit(state)

    return new_diff, consider_early_exit
