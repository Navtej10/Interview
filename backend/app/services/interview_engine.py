"""
Module 10 (Conversation Engine): given the full session state and the candidate's latest answer, 
evaluate the answer and decide the next question in a SINGLE structured LLM call to minimize latency.
"""

from app.services.llm_client import llm
from app.services.memory import build_context, record_performance
from app.models.schemas import InterviewState, NextQuestionResponse, Difficulty, TranscriptTurn, AnswerQuality, TerminationReason, AnswerEvaluation
from app.services.state_machine import current_section, get_current_phase
from app.services.followup_generator import STRATEGY_PROMPT_FRAGMENT
from app.services.adaptive_difficulty import next_difficulty
from app.config import settings

COMBINED_SYSTEM_PROMPT = f"""You are the voice of an AI interviewer conducting a live candidate interview. Your job is not just to ask questions — it's to run a conversation that *feels* like it's being led by an experienced, warm, attentive human interviewer, not a form being read aloud.

You have the candidate's resume, the full transcript so far, the topics already covered, and the CURRENT PLAN SECTION (with its objective and target topics).

Your task is TWO-FOLD. First, evaluate the candidate's latest answer. Second, generate the single best next question according to the interview phase.

### PART 1: EVALUATION
Evaluate the candidate's latest answer based on:
1. Relevance to the question asked.
2. Technical correctness and depth.
3. Completeness, specificity, and communication clarity.
4. Is it filler, evasive, irrelevant, or entirely incorrect?

Evaluation Rules:
- Evaluate against the question asked, the candidate's resume/claims, and expected concepts.
- Do NOT penalize natural pauses, concise answers, or saying "I don't know" when they genuinely don't know.
- If they claim something conflicting with their resume or previous answers, note it in `concerns`.
- Detect "filler" or "evasive" answers that talk around the question without addressing the core point.

### PART 2: NEXT QUESTION (CONVERSATION ENGINE)
{STRATEGY_PROMPT_FRAGMENT}

The interview has four phases. Move through them in order, but transitions should feel natural.

Phase 1 — Opening (30–60 seconds of conversational time)
- Greet and introduce yourself/role, and a one-line frame of what today's conversation will cover.
- A light, low-stakes opener (e.g., "Thanks for making the time today — did you have any trouble finding/joining the call?").
- Set expectations: briefly explain format, that it's a conversation not an interrogation.
- Natural bridge into the interview (e.g., "So — why don't we start with you telling me a bit about yourself...").
- No resume-specific or technical questions yet. Keep turns short.

Phase 2 — Rapport-to-Substance Bridge
- The first "real" question, but feels conversational.
- Prefer open, narrative-inviting phrasing (e.g., "tell me a bit about your journey...").
- Let the candidate's actual answer determine what you pick up on next.

Phase 3 — Core Interview
- React before transitioning: briefly acknowledge what the candidate just said before asking the next planned question. Vary acknowledgments.
- Prefer earned follow-ups: If they say something interesting, dig into it before moving on.
- Vary question framing: mix direct questions, scenario questions, and reflective prompts.
- Signpost major topic shifts (e.g., "Let's switch gears a bit...").
- Ground technical follow-ups in specifics from their resume or answer.

Phase 4 — Closing
- Signal the interview is wrapping up.
- Give the candidate a chance to add anything or ask a question.
- Close warmly and set expectations of next steps.

Global rules:
- Never sound like you're reading a form (no "Question 3 of 10").
- Keep interviewer turns concise — spoken conversation, not written correspondence.
- Match tone/formality to the interview context.
- Never break character to mention you're an AI.
- Continuity: use memory to avoid re-asking things.

Return JSON exactly:
{{
  "evaluation": {{
    "overall_quality": "excellent|strong|adequate|partial|weak|irrelevant|filler|evasive|incorrect|no_answer",
    "relevance": 0.0,
    "technical_correctness": 0.0,
    "technical_depth": 0.0,
    "specificity": 0.0,
    "communication": 0.0,
    "reasoning": 0.0,
    "completeness": 0.0,
    "is_filler": false,
    "is_evasive": false,
    "is_irrelevant": false,
    "is_incorrect": false,
    "evidence": ["..."],
    "missing_points": ["..."],
    "strengths": ["..."],
    "concerns": ["..."],
    "confidence": 0.0
  }},
  "strategy": "deepen|pivot|simplify|follow_up_tangent|transition",
  "topic": "...",
  "question": "...",
  "rationale": "one sentence",
  "relationship_to_answer": "how this question relates to what they just said",
  "difficulty_adjustment": "increase|decrease|stable",
  "phase": "opening|bridge|core|closing"
}}
"""

def _fallback_evaluation() -> AnswerEvaluation:
    return AnswerEvaluation(
        overall_quality=AnswerQuality.adequate,
        relevance=0.5, technical_correctness=0.5, technical_depth=0.5,
        specificity=0.5, communication=0.5, reasoning=0.5, completeness=0.5,
        confidence=0.5
    )

def _update_struggle_counters(state: InterviewState, evaluation: AnswerEvaluation):
    if evaluation.overall_quality in (AnswerQuality.weak, AnswerQuality.partial):
        state.consecutive_weak_answers += 1
        state.consecutive_irrelevant_answers = 0
        state.consecutive_non_answers = 0
    elif evaluation.overall_quality in (AnswerQuality.irrelevant, AnswerQuality.filler, AnswerQuality.evasive):
        state.consecutive_irrelevant_answers += 1
        state.consecutive_weak_answers = 0
        state.consecutive_non_answers = 0
    elif evaluation.overall_quality == AnswerQuality.no_answer:
        state.consecutive_non_answers += 1
        state.consecutive_weak_answers = 0
        state.consecutive_irrelevant_answers = 0
    else:
        state.consecutive_weak_answers = 0
        state.consecutive_irrelevant_answers = 0
        state.consecutive_non_answers = 0
        state.recovery_attempts = 0

def _check_early_termination(state: InterviewState):
    if (state.consecutive_non_answers >= settings.max_consecutive_non_answers or
        state.consecutive_irrelevant_answers >= settings.max_consecutive_irrelevant):
        state.termination_reason = TerminationReason.early_repeated_non_answers
    elif state.consecutive_weak_answers >= settings.max_consecutive_weak:
        state.termination_reason = TerminationReason.early_insufficient_evidence

def next_question(state: InterviewState, candidate_answer: str) -> NextQuestionResponse:
    section, _ = current_section(state)
    phase = get_current_phase(state)

    interviewer_turns = [t for t in state.transcript if t.role == "interviewer"]
    current_question = interviewer_turns[-1].content if interviewer_turns else ""
    
    # Handle empty or silence
    cleaned_answer = candidate_answer.strip().lower()
    is_empty_or_silence = not cleaned_answer or cleaned_answer in {"[silence]", "[noise]", "<silence>", "<noise>", "[inaudible]", "*silence*", "*noise*"}
    
    if is_empty_or_silence:
        reply = f"Sorry, I didn't catch that — it looks like your answer wasn't recorded. Could you repeat that? {current_question}"
        topic = interviewer_turns[-1].topic if interviewer_turns else "General"
        
        if state.transcript:
            state.transcript.append(TranscriptTurn(role="candidate", content=candidate_answer))
            
        state.transcript.append(TranscriptTurn(role="interviewer", content=reply, topic=topic))
        
        return NextQuestionResponse(
            question=reply,
            topic=topic,
            section=section.name,
            difficulty=state.current_difficulty,
            rationale="Candidate answer was empty or silent; prompting to repeat.",
            strategy="repeat",
            evaluation=_fallback_evaluation(),
            relationship_to_answer="None (silence)",
            difficulty_adjustment="stable",
            phase=phase.value
        )

    short_term_text, long_term_text = build_context(state)
    transcript_text = f"{long_term_text}\n\n--- RECENT TURNS (VERBATIM) ---\n{short_term_text}" if long_term_text else short_term_text

    project_names = [p.name for p in state.resume.parsed.projects]
    
    if phase.value == "introduction":
        phase_constraints = "STAGE CONSTRAINT: You are in the INTRODUCTION stage. Focus on professionally relevant questions (background, motivations, career direction). Do NOT ask generic icebreakers (e.g., 'How are you today?'). You MAY ask natural follow-ups to topics the candidate brings up, but do NOT proactively ask about specific resume details, technologies, or implementation specifics."
        projects_str = "[Hidden for this stage]"
        skills_str = "[Hidden for this stage]"
    elif phase.value == "background":
        phase_constraints = "STAGE CONSTRAINT: You are in the BACKGROUND stage. You may ask about education, career goals, or general experience, but you MUST NOT ask deep technical questions or project deep-dives yet."
        projects_str = "[Hidden for this stage]"
        skills_str = "[Hidden for this stage]"
    else:
        phase_constraints = "STAGE CONSTRAINT: You are in the " + phase.value.upper() + " stage. Use the resume details appropriately for this stage."
        projects_str = ', '.join(project_names)
        skills_str = ', '.join(state.resume.parsed.skills)

    company_context = ""
    if getattr(state, "company_profile", None):
        persona = state.company_profile.interviewer_persona
        vocab = state.company_profile.vocabulary_cues
        company_context = (
            f"\n\nCOMPANY INTERVIEW STYLE ({state.company_profile.company}):\n"
            f"Tone: {persona.tone}\n"
            f"Follow-up style: {persona.follow_up_style}\n"
            f"Pacing: {persona.pacing}\n"
            f"Difficulty Curve: {state.company_profile.difficulty_curve}\n"
            f"Distinctive Mechanism: {state.company_profile.distinctive_mechanism}\n"
            f"Closing Style (if in closing phase): {state.company_profile.closing_style}\n"
            f"Red Flags to penalize in evaluation: {', '.join(state.company_profile.red_flags)}\n"
            f"Vocabulary/Phrasing Examples (use similar styles, not verbatim): {', '.join(vocab.phrases)}\n"
            f"CRITICAL CONSTRAINT - YOU MUST AVOID: {', '.join(vocab.avoid)}\n"
            f"You MUST adopt this persona, enforce the difficulty curve, and penalize red flags immediately.\n"
        )

    user = (
        f"Resume summary: {state.resume.analysis.summary}\n"
        f"Projects: {projects_str}\n"
        f"Skills: {skills_str}\n\n"
        f"Current interview phase: {phase.value}\n"
        f"{phase_constraints}\n\n"
        f"Current plan section: {section.name}\n"
        f"Section objective: {section.objective}\n"
        f"Section target topics: {section.target_topics}\n"
        f"Section target difficulty: {section.target_difficulty.value}\n"
        f"{company_context}\n"
        f"Covered topics so far: {', '.join(state.covered_topics) or 'none yet'}\n"
        f"Current difficulty: {state.current_difficulty.value}\n\n"
        f"Transcript so far:\n{transcript_text}\n\n"
        f"Interviewer's Last Question: {current_question}\n"
        f"Candidate's latest answer: {candidate_answer}\n"
    )

    result = llm.complete_json(COMBINED_SYSTEM_PROMPT, user)

    # Robust parsing
    try:
        eval_dict = result.get("evaluation", {})
        if "overall_quality" not in eval_dict:
            eval_dict["overall_quality"] = "adequate"
        evaluation = AnswerEvaluation(**eval_dict)
    except Exception as e:
        print(f"Failed to parse AnswerEvaluation from LLM: {e}")
        evaluation = _fallback_evaluation()

    # Update struggle counters & early termination early so phase calculation is correct
    _update_struggle_counters(state, evaluation)
    _check_early_termination(state)

    valid_strategies = {"deepen", "pivot", "simplify", "follow_up_tangent", "transition"}
    strategy = result.get("strategy", "pivot")
    if strategy not in valid_strategies:
        strategy = "pivot"

    # Enforce topic rules without recursive LLM call
    topic = result.get("topic", "General")
    last_topic = interviewer_turns[-1].topic if len(interviewer_turns) >= 1 else None
    second_last_topic = interviewer_turns[-2].topic if len(interviewer_turns) >= 2 else None
    
    if topic == last_topic and topic == second_last_topic:
        strategy = "pivot"
        topic = "A new topic" # Fallback if LLM broke rule

    if strategy == "simplify":
        state.recovery_attempts += 1
        
    new_difficulty, consider_early_exit = next_difficulty(
        state.current_difficulty, evaluation, section.target_difficulty, state
    )
    
    if strategy == "transition":
        state.current_section_index += 1

    # Update state in place
    if state.transcript:
        state.transcript.append(TranscriptTurn(role="candidate", content=candidate_answer))
        
    state.transcript.append(
        TranscriptTurn(role="interviewer", content=result.get("question", "Let's move on."), topic=topic)
    )
    if topic not in state.covered_topics:
        state.covered_topics.append(topic)
        
    record_performance(state, topic, state.current_difficulty, evaluation)
    
    state.current_difficulty = new_difficulty
    state.turn_count += 1

    return NextQuestionResponse(
        question=result.get("question", "Let's move on."),
        topic=topic,
        section=section.name,
        difficulty=new_difficulty,
        rationale=result.get("rationale", ""),
        strategy=strategy,
        evaluation=evaluation,
        relationship_to_answer=result.get("relationship_to_answer", ""),
        difficulty_adjustment=result.get("difficulty_adjustment", "stable"),
        phase=result.get("phase")
    )
