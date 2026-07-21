from fastapi import APIRouter, UploadFile, File

from app.models.schemas import ResumeBundle
from app.services import orchestrator

router = APIRouter(prefix="/resume", tags=["resume"])


@router.post("/analyze", response_model=ResumeBundle)
async def analyze_endpoint(file: UploadFile = File(...)) -> ResumeBundle:
    file_bytes = await file.read()
    return orchestrator.analyze_resume(file_bytes, file.filename)
