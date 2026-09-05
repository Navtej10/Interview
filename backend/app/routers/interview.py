import logging
import json
from typing import Union
import asyncio
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.models.schemas import ResumeBundle, InterviewPlan, NextQuestionResponse, InterviewPhase
from app.services import orchestrator
from app.services.speech_pipeline import transcribe_speech_stream

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/interview", tags=["interview"])


class StartInterviewRequest(BaseModel):
    resume: ResumeBundle
    company_id: Union[str, None] = None

@router.get("/test_avatar")
async def test_avatar():
    from app.services.speech_pipeline import synthesize_speech_stream
    from app.services.avatar_service import avatar_service
    from app.services.behavior_engine import derive_behavior_cues
    import tempfile, os
    text = "Hello world"
    audio_stream = synthesize_speech_stream(text)
    cues = derive_behavior_cues(text, "neutral", "medium")
    
    audio_temp_fd, audio_temp = tempfile.mkstemp(suffix=".mp3")
    os.close(audio_temp_fd)
    with open(audio_temp, "wb") as f:
        async for chunk in audio_stream:
            f.write(chunk)
            
    video_temp_fd, video_temp = tempfile.mkstemp(suffix=".mp4")
    os.close(video_temp_fd)
    
    await avatar_service.render_avatar(audio_temp, cues, video_temp)
    return {"status": "ok", "video": video_temp}


class StartInterviewResponse(BaseModel):
    session_id: str
    question: str
    topic: str
    section: str
    plan: InterviewPlan
    rationale: str


class TurnRequest(BaseModel):
    session_id: str
    candidate_answer: str


@router.post("/start", response_model=StartInterviewResponse)
def start_interview(req: StartInterviewRequest) -> StartInterviewResponse:
    session_id, question, topic, section_name, plan, rationale = orchestrator.start_interview(req.resume, req.company_id)

    return StartInterviewResponse(
        session_id=session_id,
        question=question,
        topic=topic,
        section=section_name,
        plan=plan,
        rationale=rationale
    )


@router.post("/turn")
def submit_turn(req: TurnRequest) -> Union[NextQuestionResponse, dict]:
    try:
        return orchestrator.submit_answer(req.session_id, req.candidate_answer)
    except ValueError as e:
        if str(e) == "Session not found":
            raise HTTPException(404, "Session not found")
        raise HTTPException(500, str(e))


@router.websocket("/voice_turn/{session_id}")
async def voice_turn(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    try:
        # Just to check if session exists
        orchestrator.get_session(session_id)
    except ValueError:
        logger.warning(f"Rejected websocket connection: Session {session_id} not found.")
        try:
            await websocket.close(code=1008, reason="Session not found")
        except Exception:
            pass # Ignore Uvicorn/Websockets bug when closing immediately
        return

    logger.info(f"WebSocket connection established for session {session_id}")

    async def audio_generator():
        accumulated_audio = bytearray()
        try:
            while True:
                # receive() handles both text/JSON control messages and binary audio chunks
                message = await websocket.receive()
                
                if message.get("type") == "websocket.receive":
                    if "bytes" in message and message["bytes"] is not None:
                        accumulated_audio.extend(message["bytes"])
                    
                    elif "text" in message and message["text"] is not None:
                        try:
                            payload = json.loads(message["text"])
                            if payload.get("type") == "END_OF_TURN":
                                if accumulated_audio:
                                    logger.info(f"END_OF_TURN received. Processing {len(accumulated_audio)} bytes.")
                                    # Yield the fully accumulated turn audio
                                    yield bytes(accumulated_audio)
                                    # Reset for the next turn to keep the socket alive
                                    accumulated_audio = bytearray()
                                else:
                                    logger.debug("Received END_OF_TURN but no audio was accumulated.")
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON control message received: {message['text']}")
                            
                elif message.get("type") == "websocket.disconnect":
                    logger.info(f"Client disconnected gracefully (session {session_id})")
                    break
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected abruptly for session {session_id}")
        except Exception as e:
            logger.error(f"Error in audio_generator for session {session_id}: {e}", exc_info=True)

    async def send_tts(chunk: bytes):
        try:
            await websocket.send_bytes(chunk)
        except (WebSocketDisconnect, RuntimeError) as e:
            if isinstance(e, RuntimeError) and 'Cannot call "send"' not in str(e):
                raise
            logger.info(f"WebSocket disconnected while sending TTS (session {session_id})")
            raise WebSocketDisconnect(code=1006)
        except Exception as e:
            logger.error(f"Error sending TTS chunk (session {session_id}): {e}", exc_info=True)
            raise
            
    async def send_status(text: str):
        try:
            await websocket.send_text(text)
        except (WebSocketDisconnect, RuntimeError) as e:
            if isinstance(e, RuntimeError) and 'Cannot call "send"' not in str(e):
                logger.error(f"Error sending status (session {session_id}): {e}", exc_info=True)
                return
            logger.info(f"WebSocket disconnected while sending status (session {session_id})")
        except Exception as e:
            logger.error(f"Error sending status (session {session_id}): {e}", exc_info=True)

    try:
        # Pass the STT generator and TTS callback directly to the orchestrator.
        # This keeps interruption state entirely within the orchestration layer.
        await orchestrator.process_voice_stream(
            session_id, 
            audio_generator(), 
            send_tts,
            send_status
        )
    except asyncio.CancelledError:
        logger.info(f"Voice stream cancelled for session {session_id}")
    except Exception as e:
        logger.error(f"Critical WebSocket error for session {session_id}: {e}", exc_info=True)
    finally:
        if websocket.client_state.name != "DISCONNECTED":
            try:
                await websocket.close()
            except Exception as e:
                logger.error(f"Error closing websocket for session {session_id}: {e}")
        logger.info(f"WebSocket connection closed for session {session_id}")


@router.post("/end/{session_id}")
def end_interview(session_id: str) -> dict:
    try:
        return orchestrator.end_interview(session_id)
    except ValueError as e:
        if str(e) == "Session not found":
            raise HTTPException(404, "Session not found")
        raise HTTPException(500, str(e))
