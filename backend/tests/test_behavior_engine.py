from app.services.behavior_engine import derive_behavior_cues, IDLE_DEFAULTS
from app.models.schemas import Difficulty

def test_derive_behavior_cues_fallback():
    """
    Test that calling derive_behavior_cues with an unknown strategy
    safely falls back to the IDLE_DEFAULTS instead of raising an exception.
    """
    question_text = "What is your experience with React?"
    invalid_strategy = "hallucinated_strategy"
    
    # Should not raise
    cues = derive_behavior_cues(question_text, invalid_strategy, Difficulty.medium)
    
    # Must match IDLE_DEFAULTS
    assert cues.expression == IDLE_DEFAULTS["expression"]
    assert cues.blink_rate == IDLE_DEFAULTS["blink_rate"]
    assert cues.gaze_pattern == IDLE_DEFAULTS["gaze_pattern"]
    
def test_derive_behavior_cues_difficulty_variation():
    """
    Test that difficulty influences the resulting cues for a known strategy.
    """
    question_text = "Tell me more."
    
    # Same strategy, different difficulties should yield different configurations
    easy_cues = derive_behavior_cues(question_text, "deepen", Difficulty.easy)
    hard_cues = derive_behavior_cues(question_text, "deepen", Difficulty.hard)
    
    assert easy_cues.expression == "probing"
    assert hard_cues.expression == "focused"
    assert easy_cues.blink_rate > hard_cues.blink_rate
