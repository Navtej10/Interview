"""
Module 10 (Conversation Engine, informal name so far): given the full
session state and the candidate's latest answer, decide the next question.
This is the core of the product.

Design notes (read this before you touch it):

- We pass the FULL transcript + covered_topics + current_difficulty to the
  model every turn. Don't try to be clever and summarize/truncate early —
  losing track of what's been asked is the #1 way this feels broken. Only
  worry about context-window truncation once transcripts get long (see
  TODO at the bottom).
- The model must pick a strategy each turn: deepen / pivot / simplify /
  follow_up_tangent. We ask it to name the strategy explicitly in the JSON
  (not just produce a question) because that's what lets you debug *why*
  the interview went a certain direction, and lets you tune difficulty
  progression later without re-engineering the whole prompt.
- current_difficulty is nudged, not recalculated from scratch, based on the
  strategy chosen. Keep this logic OUTSIDE the LLM call — deterministic and
  cheap, and it means difficulty can't silently drift from a bad model
  output.
- As of the Interview Planner (module 5), every turn is also told which
  plan section it currently falls in (via section_for_question_index) and
  that section's objective/target_topics/target_difficulty. The model is
  told to work toward the section, not just react turn-by-turn — but the
  strategy/difficulty-nudge mechanics above still apply *within* a section,
  since a candidate can still struggle or excel inside a planned section.
"""

from app.services.llm_client import llm
from app.services.planner import section_for_question_index
from app.services.conversation_memory import summarize_if_needed
from app.models.schemas import InterviewState, NextQuestionResponse, Difficulty, TranscriptTurn
from app.services.interview_state_machine import advance
from app.services.followup_generator import STRATEGY_PROMPT_FRAGMENT
from app.services.adaptive_difficulty import next_difficulty

SYSTEM_PROMPT = f"""You are conducting a live technical interview. You have \
the candidate's resume, the full transcript so far, the topics already \
covered, and the CURRENT PLAN SECTION this part of the interview belongs \
to (with its objective and target topics). Decide the single best next \
question.

{{STRATEGY_PROMPT_FRAGMENT}}

Rules:
- Prefer the current section's target_topics when choosing what to ask about, \
  unless a strong follow_up_tangent or pivot from the candidate's last answer \
  is clearly more valuable — the plan is a guide, not a script.
- Never repeat a topic already in covered_topics unless deepening it.
- Don't ask more than 2 consecutive questions on the same topic — pivot to \
  keep the interview moving even if the topic is rich.
- Ground every question in specifics from the resume or the candidate's own \
  prior answers. Avoid generic textbook questions.
- If the current phase is WRAPPING_UP, your question should gracefully bring \
  the interview to a close (e.g., asking if they have any final thoughts or \
  a final high-level question).
- If the current phase is TRANSITIONING_SECTION, frame your question as a \
  transition to the next topic, closing out the current section.

Return JSON exactly:
{{"question": "...", "topic": "...", "strategy": "deepen|pivot|simplify|follow_up_tangent", "rationale": "one sentence, internal only"}}
"""


def next_question(state: InterviewState, candidate_answer: str) -> NextQuestionResponse:
    # Record the candidate's answer to the previous question first.
    if state.transcript:
        state.transcript.append(TranscriptTurn(role="candidate", content=candidate_answer))

    # Advance the state machine to determine the phase of the UPCOMING question.
    advance(state)

    # Question about to be generated: opening question was index 0, so the
    # next engine-generated question is at index (turn_count + 1).
    section, _ = section_for_question_index(state.plan, state.turn_count + 1)

    transcript_text = summarize_if_needed(state, max_tokens=2500)

    project_names = [p.name for p in state.resume.parsed.projects]
    user = (
        f"Resume summary: {state.resume.analysis.summary}\n"
        f"Projects: {', '.join(project_names)}\n"
        f"Skills: {', '.join(state.resume.parsed.skills)}\n\n"
        f"Current interview phase: {state.phase.value}\n"
        f"Current plan section: {section.name}\n"
        f"Section objective: {section.objective}\n"
        f"Section target topics: {section.target_topics}\n"
        f"Section target difficulty: {section.target_difficulty.value}\n\n"
        f"Covered topics so far: {', '.join(state.covered_topics) or 'none yet'}\n"
        f"Current difficulty: {state.current_difficulty.value}\n\n"
        f"Transcript so far:\n{transcript_text}\n\n"
        f"Candidate's latest answer: {candidate_answer}"
    )

    result = llm.complete_json(SYSTEM_PROMPT, user)

    new_difficulty, consider_early_exit = next_difficulty(
        state.current_difficulty, result["strategy"], section.target_difficulty, state
    )
    
    # In the future, interview_engine might use consider_early_exit to break out of the section
    # early and advance state.turn_count to the end of the section, but for now we just compute it.

    # Update state in place.
    state.transcript.append(
        TranscriptTurn(role="interviewer", content=result["question"], topic=result["topic"])
    )
    if result["topic"] not in state.covered_topics:
        state.covered_topics.append(result["topic"])
    state.current_difficulty = new_difficulty
    state.turn_count += 1

    return NextQuestionResponse(
        question=result["question"],
        topic=result["topic"],
        section=section.name,
        difficulty=new_difficulty,
        rationale=result["rationale"],
    )
