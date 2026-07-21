from typing import Union
import asyncio
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.models.schemas import ResumeBundle, InterviewPlan, NextQuestionResponse, InterviewPhase
from app.services import orchestrator, session_store
from app.services.stt_service import transcribe_stream
from app.services.tts_service import synthesize_speech_stream

router = APIRouter(prefix="/interview", tags=["interview"])


class StartInterviewRequest(BaseModel):
    resume: ResumeBundle


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
    session_id, question, topic, section_name, plan, rationale = orchestrator.start_interview(req.resume)

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
    
    state = session_store.get(session_id)
    if state is None:
        await websocket.close(code=1008, reason="Session not found")
        return

    # Keep track of the active TTS streaming task so it can be cancelled
    tts_task = None

    async def audio_generator():
        try:
            while True:
                data = await websocket.receive_bytes()
                yield data
        except WebSocketDisconnect:
            pass

    try:
        async for candidate_text in transcribe_stream(audio_generator()):
            # Interruption handling: if candidate speaks while avatar is speaking, cancel TTS
            if tts_task and not tts_task.done():
                tts_task.cancel()
            
            # Submit the turn (sync operation, but should ideally be async. We will run it in thread if necessary, 
            # but for now calling directly as the rest of the backend is sync)
            try:
                result = orchestrator.submit_answer(session_id, candidate_text)
            except Exception as e:
                await websocket.send_text(f"Error: {str(e)}")
                break

            if isinstance(result, dict) and result.get("status") == "complete":
                await websocket.send_text("Interview complete.")
                break

            # Start streaming the TTS response back to the client
            async def send_tts(text: str):
                try:
                    async for chunk in synthesize_speech_stream(text):
                        await websocket.send_bytes(chunk)
                except asyncio.CancelledError:
                    # Cancelled due to interruption
                    pass
            
            tts_task = asyncio.create_task(send_tts(result.question))
    
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if tts_task and not tts_task.done():
            tts_task.cancel()
        if not websocket.client_state.name == "DISCONNECTED":
            await websocket.close()


@router.post("/end/{session_id}")
def end_interview(session_id: str) -> dict:
    state = session_store.get(session_id)
    if state is None:
        raise HTTPException(404, "Session not found")
    state.is_complete = True
    state.phase = InterviewPhase.COMPLETE
    session_store.save(state)
    return {"session_id": session_id, "turn_count": state.turn_count}
