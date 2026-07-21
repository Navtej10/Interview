"""
Central orchestrator module.
Coordinates the workflow between routers and individual domain services.
This is the appropriate place for cross-cutting concerns like logging,
telemetry, and eventually TTS/Avatar service hooks.
"""

import uuid
import logging
from typing import Union, Tuple

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
        current_difficulty=first_section.target_difficulty,
        phase=InterviewPhase.IN_SECTION,
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

    if state.phase == InterviewPhase.COMPLETE or state.is_complete:
        return {"status": "complete"}

    try:
        result = next_question(state, candidate_answer)
        session_store.save(state)
        
        # Telemetry or Avatar hooks can be inserted here.
        # e.g., if render_avatar_mode: trigger_avatar(result.question)
        
        return result
    except Exception as e:
        logger.error(f"Error generating next question for session {session_id}: {e}")
        raise
