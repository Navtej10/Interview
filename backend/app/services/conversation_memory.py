"""
Module for extracting conversation context and signals from the interview
transcript, handling long-context summarization and derived fact extraction.
"""

from app.models.schemas import InterviewState
from app.services.llm_client import llm


def summarize_if_needed(state: InterviewState, max_tokens: int = 2000) -> str:
    """
    Returns the transcript formatted for the prompt.
    If the estimated token count of the raw transcript exceeds max_tokens,
    summarizes the older turns using an LLM and appends the last few turns
    verbatim to preserve immediate context.
    """
    if not state.transcript:
        return ""

    full_text = "\n".join(f"{t.role}: {t.content}" for t in state.transcript)
    estimated_tokens = len(full_text) // 4

    if estimated_tokens <= max_tokens or len(state.transcript) <= 6:
        # Preserve exact behavior for short transcripts
        return full_text

    # Transcript is too long, we need to compress.
    # Keep the last 4 turns (2 full interviewer-candidate exchanges) verbatim.
    recent_turns = state.transcript[-4:]
    older_turns = state.transcript[:-4]

    older_text = "\n".join(f"{t.role}: {t.content}" for t in older_turns)
    recent_text = "\n".join(f"{t.role}: {t.content}" for t in recent_turns)

    summary_prompt = """\
You are an AI assistant helping to compress the context of a technical interview. \
Summarize the following older interview turns into a concise digest. Focus \
on what was asked, the candidate's technical approaches, specific technologies \
mentioned, and areas where they showed strength or struggled. Keep it dense \
and factual."""

    # We use complete_json or just complete. Since llm_client only exposes complete_json
    # reliably in previous files... Wait, does llm_client have a basic `complete`?
    # I should check llm_client.py. If not, I can ask for JSON and extract the text.
    # I will ask for JSON with a single "summary" key to be safe.
    summary_sys = summary_prompt + '\n\nReturn JSON exactly:\n{"summary": "..."}'
    
    try:
        result = llm.complete_json(summary_sys, older_text)
        summary = result.get("summary", "")
    except Exception:
        # Fallback if summarization fails
        summary = "[Older conversation context omitted due to length]"

    return f"--- SUMMARY OF OLDER TURNS ---\n{summary}\n\n--- RECENT TURNS (VERBATIM) ---\n{recent_text}"


def extract_candidate_signals(state: InterviewState) -> dict:
    """
    Analyzes the transcript to extract lightweight derived facts (e.g., topics
    the candidate struggled on, technologies they mentioned unprompted) that
    downstream modules (like feedback or engine) can reuse.
    """
    if not state.transcript:
        return {"struggled_topics": [], "strong_topics": [], "unprompted_technologies": []}

    full_text = "\n".join(f"{t.role}: {t.content}" for t in state.transcript)
    
    sys_prompt = """\
You are an expert technical interviewer analyzing a transcript. Extract \
lightweight signals about the candidate's performance. Identify:
1. Topics the candidate clearly struggled with (e.g., needed heavy hints, gave wrong answers).
2. Topics the candidate showed strong competence in.
3. Specific technologies or tools they brought up unprompted (i.e. not mentioned in the interviewer's question).

Return JSON exactly:
{
  "struggled_topics": ["..."],
  "strong_topics": ["..."],
  "unprompted_technologies": ["..."]
}"""

    try:
        return llm.complete_json(sys_prompt, full_text)
    except Exception:
        return {"struggled_topics": [], "strong_topics": [], "unprompted_technologies": []}
