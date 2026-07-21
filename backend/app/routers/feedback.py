from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.schemas import FeedbackReport
from app.services.feedback_service import generate_written_report, debrief_turn
from app.services import session_store

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.get("/report/{session_id}", response_model=FeedbackReport)
def written_report(session_id: str) -> FeedbackReport:
    state = session_store.get(session_id)
    if state is None:
        raise HTTPException(404, "Session not found")
    return generate_written_report(state)


class DebriefTurnRequest(BaseModel):
    session_id: str
    candidate_message: str


@router.post("/debrief")
def debrief(req: DebriefTurnRequest) -> dict:
    state = session_store.get(req.session_id)
    if state is None:
        raise HTTPException(404, "Session not found")
    reply = debrief_turn(state, req.candidate_message)
    return {"reply": reply}
