from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.schemas import FeedbackReport
from app.services import orchestrator

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.get("/report/{session_id}", response_model=FeedbackReport)
def written_report(session_id: str) -> FeedbackReport:
    try:
        return orchestrator.get_written_report(session_id)
    except ValueError as e:
        if str(e) == "Session not found":
            raise HTTPException(404, "Session not found")
        raise HTTPException(500, str(e))


class DebriefTurnRequest(BaseModel):
    session_id: str
    candidate_message: str


@router.post("/debrief")
def debrief(req: DebriefTurnRequest) -> dict:
    try:
        reply = orchestrator.get_debrief_reply(req.session_id, req.candidate_message)
        return {"reply": reply}
    except ValueError as e:
        if str(e) == "Session not found":
            raise HTTPException(404, "Session not found")
        raise HTTPException(500, str(e))
