"""
Module for adaptively nudging the difficulty of the interview purely deterministically.
"""

from app.models.schemas import Difficulty, InterviewState

_DIFFICULTY_ORDER = [Difficulty.easy, Difficulty.medium, Difficulty.hard]

def _has_struggled_consecutively(state: InterviewState, n: int = 2) -> bool:
    """
    Deterministic heuristic to guess if the candidate struggled on N consecutive turns,
    by examining the transcript directly.
    """
    candidate_turns = [t for t in state.transcript if t.role == "candidate"]
    if len(candidate_turns) < n:
        return False

    struggle_phrases = [
        "don't know", "not sure", "not familiar", "forgot", 
        "can't remember", "no idea", "haven't used"
    ]
    
    for turn in candidate_turns[-n:]:
        text = turn.content.lower()
        if not any(phrase in text for phrase in struggle_phrases) and len(text.split()) > 5:
            # If they didn't use a struggle phrase and wrote more than 5 words, 
            # assume no obvious struggle
            return False
            
    return True

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
    elif strategy in ("pivot", "follow_up_tangent"):
        # Hold steady unless they struggled on 2 consecutive turns
        if _has_struggled_consecutively(state, 2):
            if current_idx > 0:
                new_idx -= 1

    # Enforce bounds
    new_idx = max(0, min(len(_DIFFICULTY_ORDER) - 1, new_idx))
    new_diff = _DIFFICULTY_ORDER[new_idx]
    
    # Check early exit condition:
    # "never let difficulty stay below section.target_difficulty by more than one step for more than 2 consecutive turns"
    # To check this purely deterministically without schema changes, we can look at whether the new difficulty
    # is still below (target - 1) AND if the candidate has been struggling for > 2 turns.
    consider_early_exit = False
    if new_idx < target_idx - 1:
        if _has_struggled_consecutively(state, 3):
            consider_early_exit = True

    return new_diff, consider_early_exit
