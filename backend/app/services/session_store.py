"""
Deliberately dumb in-memory store keyed by session_id. Fine for local dev
and single-process demos. When you're ready for multi-user/production,
swap the dict for Redis (session TTL matters — interviews are transient)
without touching any calling code, since everything goes through get/save.
"""

from app.models.schemas import InterviewState

_sessions: dict[str, InterviewState] = {}


def save(state: InterviewState) -> None:
    _sessions[state.session_id] = state


def get(session_id: str) -> InterviewState | None:
    return _sessions.get(session_id)


def delete(session_id: str) -> None:
    _sessions.pop(session_id, None)
