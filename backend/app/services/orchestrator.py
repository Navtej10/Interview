"""
Central orchestrator module.
Coordinates the workflow between routers and individual domain services.
This is the appropriate place for cross-cutting concerns like logging,
telemetry, and eventually TTS/Avatar service hooks.
"""

import uuid
import logging
import asyncio
from typing import Union, Tuple, AsyncIterator, Callable

from app.models.schemas import (
    ResumeBundle,
    InterviewPlan,
    InterviewState,
    TranscriptTurn,
    NextQuestionResponse,
    InterviewPhase
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


def start_interview(resume: ResumeBundle) -> tuple[str, str, str, str, InterviewPlan, str]:
    """
    Coordinates the initialization of a new interview session.
    Returns: (session_id, question, topic, section_name, plan, rationale)
    """
    logger.info("Starting new interview session")
    session_id = str(uuid.uuid4())

    plan = generate_plan(resume)
    first_section, _ = section_for_question_index(plan, 0)
    question, topic, rationale = generate_opening_question(resume, first_section)

    state = InterviewState(
        session_id=session_id,
        resume=resume,
        plan=plan,
        transcript=[TranscriptTurn(role="interviewer", content=question, topic=topic)],
        covered_topics=[topic],
        current_difficulty=first_section.target_difficulty
    )
    session_store.save(state)
    logger.info(f"Session {session_id} started successfully")

    return session_id, question, topic, first_section.name, plan, rationale


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
        from app.services.avatar_pipeline import render_avatar_video, LivePortraitError
        from app.services.behavior_engine import derive_behavior_cues, Difficulty
    except ImportError:
        LivePortraitError = type("LivePortraitError", (Exception,), {})
        synthesize_speech = None
        render_avatar_video = None
        derive_behavior_cues = None

    try:
        if synthesize_speech is None:
            raise NotImplementedError("speech_pipeline not installed")
        
        cues = derive_behavior_cues(text, "neutral", Difficulty.medium)
        
        async def run_pipeline():
            audio_path = await synthesize_speech(text, "output.wav")
            await render_avatar_video(audio_path, cues, "avatar_output.mp4")

        # Since this is a synchronous path, we use asyncio.run to await the generation.
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(run_pipeline())
        except RuntimeError:
            asyncio.run(run_pipeline())
    except (NotImplementedError, LivePortraitError, Exception) as e:
        logger.warning(f"Voice/Avatar pipeline failed, falling back to text-only mode: {e}")

async def process_voice_stream(
    session_id: str, 
    audio_generator: AsyncIterator[bytes], 
    send_tts: Callable[[bytes], asyncio.Task], 
    send_status: Callable[[str], asyncio.Task]
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
    from app.services.avatar_pipeline import render_avatar_video_stream
    from app.services.behavior_engine import derive_behavior_cues
    
    async def send_avatar_wrapper(text: str, result_dict: dict):
        """
        Coordinates generating the TTS audio and Avatar video, then sending the complete video.
        Any exceptions during avatar generation are explicitly logged and not swallowed.
        """
        try:
            logger.info(f"Generating avatar response for: {text}")
            audio_stream = synthesize_speech_stream(text)
            diff = result_dict.get("difficulty", "medium")
            strat = result_dict.get("rationale", "neutral")
            cues = derive_behavior_cues(text, strat, diff)
            
            # This generates the complete turn-based video and yields it back in chunks
            async for chunk in render_avatar_video_stream(audio_stream, cues):
                await send_tts(chunk)
                
            logger.info("Avatar response sent successfully.")
        except asyncio.CancelledError:
            logger.info("Avatar playback was interrupted by the client.")
            raise
        except Exception as e:
            logger.error(f"Critical error during avatar generation/playback: {e}", exc_info=True)
            # Never swallow avatar exceptions
            await send_status(f"Avatar error: {e}")
            raise

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
        return
    except Exception as e:
        logger.error(f"Failed to play opening question: {e}", exc_info=True)
        # We abort the stream early if the avatar pipeline is broken
        return

    # 2. Sequential turn processing loop
    try:
        # Transcribe candidate audio per explicit turn
        async for candidate_text in transcribe_speech_stream(audio_generator):
            logger.info(f"Received candidate transcript: {candidate_text}")
            
            # 3. Generate Next Question
            try:
                result = submit_answer(session_id, candidate_text)
            except Exception as e:
                logger.error(f"Failed to generate next question: {e}", exc_info=True)
                await send_status(f"Error: {str(e)}")
                break

            # 4. Check for Interview Completion
            if isinstance(result, dict) and result.get("status") == "complete":
                logger.info(f"Interview {session_id} is complete.")
                await send_status("Interview complete.")
                break
                
            # Send transcript update to frontend
            import json
            await send_status(json.dumps({
                "type": "transcript",
                "candidate": candidate_text,
                "interviewer": result.question
            }))
            
            # 5. Render & Send Avatar Response
            try:
                await send_avatar_wrapper(
                    result.question, 
                    result.model_dump() if hasattr(result, 'model_dump') else result
                )
            except Exception as e:
                logger.error(f"Avatar rendering failed for turn. Stopping voice loop: {e}", exc_info=True)
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
    # The phase is dynamically derived from state, so we don't need to mutate state.phase anymore.
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
