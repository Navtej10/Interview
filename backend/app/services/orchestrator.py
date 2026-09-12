"""
Central orchestrator module.
Coordinates the workflow between routers and individual domain services.
This is the appropriate place for cross-cutting concerns like logging,
telemetry, and eventually TTS/Avatar service hooks.
"""

import uuid
import logging
import asyncio
import json
from typing import Union, Tuple, AsyncIterator, Callable

from app.models.schemas import (
    ResumeBundle,
    InterviewPlan,
    InterviewState,
    TranscriptTurn,
    NextQuestionResponse,
    InterviewPhase,
    Difficulty
)
from app.services.resume_parser import parse_resume
from app.services.resume_analysis import analyze
from app.services.knowledge_graph import build_graph

from app.services.planner import generate_plan, section_for_question_index
from app.services.question_generator import generate_opening_question
from app.services.interview_engine import next_question
from app.services.feedback_service import generate_written_report, debrief_turn
from app.models.schemas import FeedbackReport
from app.services import session_store
from app.services.company_profiles import get_company_profile

logger = logging.getLogger(__name__)


def analyze_resume(file_bytes: bytes, filename: str) -> ResumeBundle:
    """
    Coordinates the resume parsing, graph building, and analysis pipeline.
    """
    logger.info(f"Starting resume analysis for file: {filename}")
    try:
        parsed = parse_resume(file_bytes, filename)
        graph = build_graph(parsed)
        analysis = analyze(parsed, graph)
        return ResumeBundle(parsed=parsed, analysis=analysis, graph=graph)
    except Exception as e:
        logger.error(f"Failed to analyze resume: {e}")
        raise


def start_interview(resume: ResumeBundle, company_id: Union[str, None] = None) -> tuple[str, str, str, str, InterviewPlan, str]:
    """
    Coordinates the initialization of a new interview session.
    Returns: (session_id, question, topic, section_name, plan, rationale)
    """
    logger.info(f"Starting new interview session for company {company_id}")
    session_id = str(uuid.uuid4())

    company_profile = get_company_profile(company_id) if company_id else get_company_profile("default")
    if company_profile is None:
        raise ValueError("Company profile not found")

    # Map seniority
    exp_level = resume.analysis.candidate_profile.experience_level.lower()
    career_stage = resume.analysis.candidate_profile.career_stage.lower()
    
    seniority = "mid"
    if any(x in exp_level or x in career_stage for x in ["student", "junior", "entry", "intern"]):
        seniority = "entry"
    elif any(x in exp_level or x in career_stage for x in ["staff", "principal", "director"]):
        seniority = "staff_plus"
    elif any(x in exp_level or x in career_stage for x in ["senior", "lead", "manager"]):
        seniority = "senior"

    plan = generate_plan(resume, company_profile, seniority)
    first_section, _ = section_for_question_index(plan, 0)
    greeting, question, topic, rationale = generate_opening_question(resume, first_section)
    combined_question = f"{greeting} {question}"

    modifier = company_profile.seniority_modifiers.get(seniority, company_profile.seniority_modifiers.get("mid"))
    diff_map = {
        "baseline": Difficulty.easy,
        "moderate": Difficulty.medium,
        "elevated": Difficulty.hard
    }
    start_diff = diff_map.get(modifier.difficulty_start.lower(), Difficulty.medium) if modifier else Difficulty.medium

    state = InterviewState(
        session_id=session_id,
        resume=resume,
        plan=plan,
        company_profile=company_profile,
        transcript=[TranscriptTurn(role="interviewer", content=combined_question, topic=topic)],
        covered_topics=[topic],
        current_difficulty=start_diff,
        # we can just store seniority on state by attaching it to the company profile or tracking it, 
        # actually we don't have a field for it, let's just use the modifier when needed in engines
    )
    
    # Store the determined seniority dynamically on the profile instance for easy access downstream
    setattr(state, "inferred_seniority", seniority)
    session_store.save(state)
    logger.info(f"Session {session_id} started successfully")

    return session_id, combined_question, topic, first_section.name, plan, rationale


def submit_answer(session_id: str, candidate_answer: str) -> Union[NextQuestionResponse, dict]:
    """
    Coordinates the processing of a candidate's answer and generating the next turn.
    Returns a NextQuestionResponse, or a 'session complete' dict if the interview is finished.
    """
    logger.info(f"Processing turn for session {session_id}")
    
    state = session_store.get(session_id)
    if state is None:
        raise ValueError("Session not found")

    if state.is_complete:
        return {"status": "complete"}

    try:
        result = next_question(state, candidate_answer)
        
        # Hard ceiling enforcement
        hard_ceiling = state.plan.total_estimated_turns + 2
        if state.turn_count >= hard_ceiling or getattr(result, 'isFinalTurn', False):
            state.is_complete = True
            
        session_store.save(state)
        
        # Telemetry or Avatar hooks can be inserted here.
        render_interviewer_turn(result.question)
        
        return result
    except Exception as e:
        logger.error(f"Error generating next question for session {session_id}: {e}")
        raise

def render_interviewer_turn(text: str):
    """
    Optional hook for rendering the interviewer's speech/avatar synchronously.
    (WebSocket streaming handles its own async TTS, but this exists for batch/webhook flows).
    Catches NotImplementedError or other failures from stubs and falls back gracefully.
    """
    try:
        from app.services.speech_pipeline import synthesize_speech
        from app.services.avatar_service import avatar_service, AvatarError
        from app.services.behavior_engine import derive_behavior_cues
    except ImportError:
        AvatarError = type("AvatarError", (Exception,), {})
        synthesize_speech = None
        avatar_service = None
        derive_behavior_cues = None

    try:
        if synthesize_speech is None or derive_behavior_cues is None or avatar_service is None:
            raise NotImplementedError("speech_pipeline or avatar_service not installed")
        
        cues = derive_behavior_cues(text, "neutral", Difficulty.medium)
        
        async def run_pipeline():
            audio_path = await synthesize_speech(text, "output.wav")
            await avatar_service.render_avatar(audio_path, cues, "avatar_output.mp4")  # type: ignore

        # Since this is a synchronous path, we use asyncio.run to await the generation.
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(run_pipeline())
        except RuntimeError:
            asyncio.run(run_pipeline())
    except (NotImplementedError, AvatarError, Exception) as e:
        logger.warning(f"Voice/Avatar pipeline failed, falling back to text-only mode: {e}")

def _build_transcription_prompt(state: InterviewState) -> str:
    """
    Best-effort domain vocabulary hint so Whisper is less likely to mis-hear
    the candidate's name, employers, and technical terms from their resume.
    """
    try:
        parsed = state.resume.parsed
        name = getattr(parsed, "name", None) or getattr(parsed, "full_name", None)
        skills = getattr(parsed, "skills", None) or []
        companies = [
            getattr(exp, "company", None)
            for exp in (getattr(parsed, "experience", None) or [])
        ]
        terms = [t for t in [name, *skills, *companies] if t]
        if terms:
            return "Interview transcript. Relevant terms: " + ", ".join(terms[:25])
    except Exception as e:
        logger.debug(f"Could not build transcription prompt from resume: {e}")
    return "Interview transcript for a technical job candidate."

from typing import AsyncIterator, Callable, Union, Awaitable

async def process_voice_stream(
    session_id: str, 
    audio_generator: AsyncIterator[bytes], 
    send_tts: Callable[[bytes], Awaitable[None]], 
    send_status: Callable[[str], Awaitable[None]],
    is_interrupted: Union[Callable[[], bool], None] = None
):
    """
    Coordinates the voice interview pipeline as a series of explicit turns.
    For each turn:
    1. Render & send the interviewer's question (video)
    2. Wait for the candidate to speak (receive audio)
    3. Transcribe candidate audio
    4. Generate next question
    5. Repeat
    """
    from app.services.speech_pipeline import transcribe_speech_stream, synthesize_speech_stream
    from app.services.avatar_service import avatar_service, AvatarError
    from app.services.behavior_engine import derive_behavior_cues
    import tempfile
    import os
    
    async def send_avatar_wrapper(text: str, result_dict: dict):
        """
        Coordinates generating the TTS audio and Avatar video, then sending the complete video.
        Any exceptions during avatar generation are explicitly logged and not swallowed.
        """
        audio_temp = None
        video_temp = None
        try:
            logger.info(f"Generating avatar response for: {text}")
            print(f"DEBUG: Generating avatar response for: {text}", flush=True)
            audio_stream = synthesize_speech_stream(text)
            diff = result_dict.get("difficulty", "medium")
            strat = result_dict.get("rationale", "neutral")
            cues = derive_behavior_cues(text, strat, diff)
            print("DEBUG: Accumulated cues, making temp audio file", flush=True)
            
            # 1. Accumulate audio chunks to a temp file
            audio_temp_fd, audio_temp = tempfile.mkstemp(suffix=".mp3")
            os.close(audio_temp_fd)
            with open(audio_temp, "wb") as f:
                async for chunk in audio_stream:
                    # Allow interrupt during TTS generation if needed, though this is fast
                    if is_interrupted and is_interrupted():
                        logger.info("Avatar generation interrupted by candidate.")
                        return
                    f.write(chunk)
            print("DEBUG: Rendering avatar video", flush=True)
                    
            if is_interrupted and is_interrupted():
                logger.info("Avatar generation interrupted by candidate before rendering.")
                return

            # 2. Render Avatar Video
            video_temp_fd, video_temp = tempfile.mkstemp(suffix=".mp4")
            os.close(video_temp_fd)
            print("DEBUG: Awaiting avatar_service.render_avatar", flush=True)
            await avatar_service.render_avatar(audio_temp, cues, video_temp)
            print("DEBUG: Avatar rendered, streaming back video chunks", flush=True)
            
            if is_interrupted and is_interrupted():
                logger.info("Avatar playback interrupted by candidate before streaming.")
                return

            # 3. Stream back the completed video in chunks
            await send_status(json.dumps({"type": "state", "value": "ai_speaking"}))
            with open(video_temp, "rb") as f:
                while True:
                    if is_interrupted and is_interrupted():
                        logger.info("Avatar playback interrupted by candidate mid-stream.")
                        break
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    await send_tts(chunk)
            
            # Only reset state to listening if we weren't interrupted. If we were,
            # the router state is already user_speaking.
            if not (is_interrupted and is_interrupted()):
                await send_status(json.dumps({"type": "state", "value": "listening"}))
                logger.info("Avatar response sent successfully.")
        except asyncio.CancelledError:
            logger.info("Avatar playback was interrupted by the client.")
            raise
        except Exception as e:
            print(f"DEBUG: Critical error in send_avatar_wrapper: {e}")
            logger.error(f"Critical error during avatar generation/playback: {e}", exc_info=True)
            # Never swallow avatar exceptions
            await send_status(f"Avatar error: {e}")
            raise
        finally:
            for tmp_file in [audio_temp, video_temp]:
                if tmp_file and os.path.exists(tmp_file):
                    try:
                        os.unlink(tmp_file)
                    except Exception as cleanup_err:
                        logger.error(f"Failed to clean up temp file {tmp_file}: {cleanup_err}", exc_info=True)

    # 1. Play the opening question sequentially
    try:
        state = get_session(session_id)
        if state.transcript and state.transcript[-1].role == "interviewer":
            await send_avatar_wrapper(
                state.transcript[-1].content, 
                {"difficulty": state.current_difficulty.value, "rationale": "neutral"}
            )
    except asyncio.CancelledError:
        logger.info("Voice stream was cancelled during opening question.")
        print("DEBUG: Cancelled during opening question")
        return
    except Exception as e:
        logger.error(f"Failed to play opening question: {e}", exc_info=True)
        print(f"DEBUG: Failed to play opening question: {e}")
        # We abort the stream early if the avatar pipeline is broken
        return

    # 2. Sequential turn processing loop
    try:
        # Transcribe candidate audio per explicit turn
        prompt = _build_transcription_prompt(state)
        async for candidate_text in transcribe_speech_stream(audio_generator, initial_prompt=prompt):
            logger.info(f"Received candidate transcript: {candidate_text}")
            
            # 3. Generate Next Question
            try:
                result = submit_answer(session_id, candidate_text)
            except Exception as e:
                logger.error(f"Failed to generate next question: {e}", exc_info=True)
                await send_status(f"Error: {str(e)}")
                break

            # 4. Check for Interview Completion
            is_complete = False
            if isinstance(result, dict):
                if result.get("status") == "complete":
                    is_complete = True
            elif getattr(result, 'isFinalTurn', False) or get_session(session_id).is_complete:
                is_complete = True

            # Send transcript update to frontend
            await send_status(json.dumps({
                "type": "transcript",
                "candidate": candidate_text,
                "interviewer": result.question if not isinstance(result, dict) else ""
            }))
            
            # 5. Render & Send Avatar Response (even for final turn)
            if not isinstance(result, dict):
                try:
                    await send_avatar_wrapper(
                        result.question, 
                        result.model_dump()
                    )
                except Exception as e:
                    logger.error(f"Avatar rendering failed for turn. Stopping voice loop: {e}", exc_info=True)
                    break
            
            if is_complete:
                logger.info(f"Interview {session_id} is complete.")
                end_interview(session_id)
                await send_status(json.dumps({"type": "state", "value": "completed"}))
                break

    except asyncio.CancelledError:
        logger.info(f"Voice stream for session {session_id} was interrupted/cancelled.")
    except Exception as e:
        logger.error(f"Unexpected error in voice stream loop: {e}", exc_info=True)

def get_session(session_id: str) -> InterviewState:
    state = session_store.get(session_id)
    if state is None:
        raise ValueError("Session not found")
    return state

def end_interview(session_id: str) -> dict:
    logger.info(f"Ending interview for session {session_id}")
    state = get_session(session_id)
        
    state.is_complete = True
    if state.termination_reason is None:
        from app.models.schemas import TerminationReason
        state.termination_reason = TerminationReason.normal_completion
    session_store.save(state)
    return {"session_id": session_id, "turn_count": state.turn_count}

def get_written_report(session_id: str) -> FeedbackReport:
    logger.info(f"Generating written report for session {session_id}")
    state = session_store.get(session_id)
    if state is None:
        raise ValueError("Session not found")
    return generate_written_report(state)

def get_debrief_reply(session_id: str, candidate_message: str) -> str:
    logger.info(f"Processing debrief turn for session {session_id}")
    state = session_store.get(session_id)
    if state is None:
        raise ValueError("Session not found")
    return debrief_turn(state, candidate_message)
