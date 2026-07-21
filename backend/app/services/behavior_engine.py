"""
Behavior Engine.
Deterministically derives non-verbal avatar cues (expressions, gaze, blinking)
from the conversational state, avoiding an additional LLM call.
"""

import re
from app.models.schemas import Difficulty, BehaviorCues


def derive_behavior_cues(question_text: str, strategy: str, difficulty: Difficulty) -> BehaviorCues:
    """
    Derives avatar behavior cues based on the question text, conversation strategy,
    and current difficulty.
    """
    # 1. Expression Mapping
    expression = "neutral"
    if strategy == "simplify":
        expression = "encouraging"
    elif strategy == "deepen":
        expression = "probing"
    elif strategy == "pivot":
        expression = "thoughtful"
    elif strategy == "follow_up_tangent":
        expression = "neutral"
        
    # Overrides based on difficulty
    if difficulty == Difficulty.hard and expression == "neutral":
        expression = "probing"

    # 2. Idle Parameters
    # Harder questions -> more focused gaze, slower blink rate
    if difficulty == Difficulty.hard:
        blink_rate = 1.0  # Slow blinks
        gaze_pattern = "direct"
    elif difficulty == Difficulty.medium:
        blink_rate = 1.5  # Normal blinks
        gaze_pattern = "normal"
    else:
        blink_rate = 2.0  # Faster/relaxed blinks
        gaze_pattern = "wandering"

    # 3. Emphasis Points (Simple heuristic: extract capitalized non-start words or quoted text)
    emphasis_points = []
    
    # Extract words in quotes
    quotes = re.findall(r'["\']([^"\']+)["\']', question_text)
    emphasis_points.extend(quotes)
    
    return BehaviorCues(
        emphasis_points=emphasis_points,
        expression=expression,
        blink_rate=blink_rate,
        gaze_pattern=gaze_pattern
    )
