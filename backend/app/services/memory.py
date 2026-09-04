from app.models.schemas import InterviewState, PerformanceNote, Difficulty, AnswerEvaluation
from app.config import settings

def build_context(state: InterviewState) -> tuple[str, str]:
    """
    Splits the interview transcript into short-term (verbatim) and long-term
    (summarized via PerformanceNotes) context based on SHORT_TERM_WINDOW.
    """
    window = settings.short_term_window
    
    if len(state.transcript) <= window:
        short_term_turns = state.transcript
        older_turns_existed = False
    else:
        short_term_turns = state.transcript[-window:]
        older_turns_existed = True

    short_term_text = "\n".join(f"{t.role}: {t.content}" for t in short_term_turns)
    
    # Cap the long term text to avoid unbounded growth as the interview gets long.
    # We will keep a representative note per topic.
    # Note on tradeoff: We lose the exact sequence of performance fluctuations
    # over a single topic, but we preserve the most recent signal for each topic
    # without blowing up the context window.
    representative_notes = {}
    for note in state.performance_notes:
        representative_notes[note.topic] = note
    
    if not representative_notes and not older_turns_existed:
        long_term_text = ""
    elif not representative_notes and older_turns_existed:
        long_term_text = "[Older conversation context omitted]"
    else:
        notes_str = "; ".join(f"[{n.topic} - Diff: {n.difficulty.value}, Quality: {n.evaluation.overall_quality.value}]" for n in representative_notes.values())
        long_term_text = f"--- SUMMARY OF OLDER TURNS (Performance) ---\n{notes_str}"

    return short_term_text, long_term_text


def record_performance(state: InterviewState, topic: str, difficulty: Difficulty, evaluation: AnswerEvaluation) -> None:
    """
    Records a PerformanceNote for a given turn.
    Called once per turn by the engine.
    """
    note = PerformanceNote(topic=topic, difficulty=difficulty, evaluation=evaluation)
    state.performance_notes.append(note)
