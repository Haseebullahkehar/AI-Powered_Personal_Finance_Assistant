"""
Simple in-memory conversation history manager.
Stores per-session message history for multi-turn support.
"""

from collections import defaultdict
from datetime import datetime

# In-memory store: session_id -> list of messages
_sessions: dict[str, list[dict]] = defaultdict(list)
MAX_HISTORY = 20  # Keep last 20 turns per session


def add_message(session_id: str, role: str, content: str):
    """Add a message to a session's history."""
    _sessions[session_id].append({
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
    })
    # Trim to max history (keep most recent)
    if len(_sessions[session_id]) > MAX_HISTORY:
        _sessions[session_id] = _sessions[session_id][-MAX_HISTORY:]


def get_history(session_id: str) -> list[dict]:
    """Return conversation history for a session (without timestamps)."""
    return [
        {"role": m["role"], "content": m["content"]}
        for m in _sessions[session_id]
    ]


def clear_history(session_id: str):
    """Clear history for a session."""
    _sessions[session_id] = []


def get_all_sessions() -> list[str]:
    return list(_sessions.keys())
