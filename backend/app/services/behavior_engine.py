"""
Behavior Engine.
Deterministically derives non-verbal avatar cues (expressions, gaze, blinking)
from the conversational state, avoiding an additional LLM call. This keeps the
behavior generation fast, lightweight, and consistent.
"""

import re
import logging
from typing import Dict, Any, Optional

from app.models.schemas import Difficulty, BehaviorCues

logger = logging.getLogger(__name__)

# Base idle behaviors to be used as fallbacks or during waiting periods.
# Can be consumed directly by the avatar rendering loop.
IDLE_PRESETS = {
    "default": {
        "expression": "neutral",
        "blink_rate": 1.5,
        "gaze_pattern": "direct"
    },
    "listening": {
        "expression": "thoughtful",
        "blink_rate": 2.0,
        "gaze_pattern": "normal"
    },
    "processing": {
        "expression": "focused",
        "blink_rate": 1.0,
        "gaze_pattern": "wandering"
    }
}

# Deterministic mapping: strategy -> difficulty -> cues
# Extensible format makes it easy to add new states and expressions.
_STRATEGY_CUES: Dict[str, Dict[Difficulty, Dict[str, Any]]] = {
    "simplify": {
        Difficulty.easy: {"expression": "encouraging", "blink_rate": 2.0, "gaze_pattern": "wandering"},
        Difficulty.medium: {"expression": "encouraging", "blink_rate": 1.5, "gaze_pattern": "normal"},
        Difficulty.hard: {"expression": "neutral", "blink_rate": 1.0, "gaze_pattern": "direct"},
    },
    "deepen": {
        Difficulty.easy: {"expression": "probing", "blink_rate": 1.5, "gaze_pattern": "normal"},
        Difficulty.medium: {"expression": "probing", "blink_rate": 1.2, "gaze_pattern": "direct"},
        Difficulty.hard: {"expression": "focused", "blink_rate": 0.8, "gaze_pattern": "intense_direct"},
    },
    "pivot": {
        Difficulty.easy: {"expression": "thoughtful", "blink_rate": 2.0, "gaze_pattern": "wandering"},
        Difficulty.medium: {"expression": "thoughtful", "blink_rate": 1.5, "gaze_pattern": "normal"},
        Difficulty.hard: {"expression": "thoughtful", "blink_rate": 1.0, "gaze_pattern": "direct"},
    },
    "follow_up_tangent": {
        Difficulty.easy: {"expression": "neutral", "blink_rate": 2.0, "gaze_pattern": "wandering"},
        Difficulty.medium: {"expression": "neutral", "blink_rate": 1.5, "gaze_pattern": "normal"},
        Difficulty.hard: {"expression": "neutral", "blink_rate": 1.0, "gaze_pattern": "direct"},
    },
    "neutral": {
        Difficulty.easy: {"expression": "neutral", "blink_rate": 1.5, "gaze_pattern": "normal"},
        Difficulty.medium: {"expression": "neutral", "blink_rate": 1.5, "gaze_pattern": "direct"},
        Difficulty.hard: {"expression": "neutral", "blink_rate": 1.2, "gaze_pattern": "intense_direct"},
    }
}


def get_idle_behavior(preset_name: str = "default") -> BehaviorCues:
    """
    Returns behavior cues for idle states (e.g., listening, processing).
    Provides safe defaults if an unknown preset is requested.
    """
    if preset_name not in IDLE_PRESETS:
        logger.warning(f"Unknown idle preset '{preset_name}', falling back to 'default'.")
        preset_name = "default"
        
    cues_dict = IDLE_PRESETS[preset_name]
    return BehaviorCues(
        emphasis_points=[],
        expression=cues_dict["expression"],
        blink_rate=cues_dict["blink_rate"],
        gaze_pattern=cues_dict["gaze_pattern"]
    )


def derive_behavior_cues(
    question_text: str, 
    strategy: Optional[str], 
    difficulty: Any
) -> BehaviorCues:
    """
    Derives avatar behavior cues based on the question text, conversation strategy,
    and current difficulty level.
    
    Args:
        question_text: The text to be spoken by the avatar.
        strategy: The conversational strategy (e.g., 'deepen', 'simplify').
        difficulty: The current difficulty level of the interview.
        
    Returns:
        BehaviorCues: Deterministically generated behavioral parameters.
    """
    # 1. Validation and safe defaults for inputs
    if not isinstance(strategy, str) or not strategy.strip():
        logger.debug("Invalid or missing strategy provided. Defaulting to 'neutral'.")
        strategy = "neutral"
    else:
        strategy = strategy.strip().lower()

    if isinstance(difficulty, str):
        try:
            difficulty = Difficulty(difficulty.lower())
        except ValueError:
            logger.warning(f"Invalid difficulty string '{difficulty}'. Defaulting to medium.")
            difficulty = Difficulty.medium
    elif not isinstance(difficulty, Difficulty):
        logger.warning(f"Invalid difficulty type '{type(difficulty)}'. Defaulting to medium.")
        difficulty = Difficulty.medium

    # 2. Lookup from dictionary, with safe fallback to generic default behavior
    base_defaults = IDLE_PRESETS["default"]
    
    if strategy not in _STRATEGY_CUES:
        logger.warning(f"Unknown strategy '{strategy}'. Using base default behaviors.")
        cues_dict = base_defaults
    else:
        # Get strategy cues, safely falling back if difficulty mapping is missing
        cues_dict = _STRATEGY_CUES[strategy].get(difficulty, base_defaults)

    expression = cues_dict.get("expression", base_defaults["expression"])
    blink_rate = cues_dict.get("blink_rate", base_defaults["blink_rate"])
    gaze_pattern = cues_dict.get("gaze_pattern", base_defaults["gaze_pattern"])

    # 3. Emphasis Points (Simple heuristic: extract quoted text for emphasis)
    emphasis_points = []
    if question_text and isinstance(question_text, str):
        quotes = re.findall(r'["\']([^"\']+)["\']', question_text)
        emphasis_points.extend(quotes)
    
    return BehaviorCues(
        emphasis_points=emphasis_points,
        expression=expression,
        blink_rate=blink_rate,
        gaze_pattern=gaze_pattern
    )
