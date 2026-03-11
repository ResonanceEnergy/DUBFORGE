"""
DUBFORGE — Session Persistence  (Session 147)

Save and load SUBPHONICS chat sessions to/from JSON files.
Enables resuming conversations across server restarts.
"""

import json
import time
from pathlib import Path

from engine.subphonics import ChatMessage, ChatSession, SubphonicsEngine

from engine.config_loader import PHI
SESSION_DIR = Path("output/memory/sessions")


def save_session(session: ChatSession,
                 output_dir: str | Path = SESSION_DIR) -> str:
    """Save a chat session to JSON file. Returns file path."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    filename = f"{session.session_id}.json"
    path = out / filename

    data = session.to_dict()
    data["saved_at"] = time.time()
    data["message_count"] = len(session.messages)

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    return str(path)


def load_session(session_id: str,
                 input_dir: str | Path = SESSION_DIR) -> ChatSession | None:
    """Load a chat session from JSON file. Returns None if not found."""
    path = Path(input_dir) / f"{session_id}.json"
    if not path.exists():
        return None

    with open(path) as f:
        data = json.load(f)

    session = ChatSession(session_id=data["session_id"])
    session.context = data.get("context", {})

    for msg_data in data.get("messages", []):
        msg = ChatMessage(
            role=msg_data["role"],
            content=msg_data["content"],
            timestamp=msg_data.get("timestamp", 0.0),
            metadata=msg_data.get("metadata", {}),
        )
        session.messages.append(msg)

    return session


def list_sessions(input_dir: str | Path = SESSION_DIR) -> list[dict]:
    """List all saved sessions with metadata."""
    d = Path(input_dir)
    if not d.exists():
        return []

    sessions = []
    for path in sorted(d.glob("*.json")):
        try:
            with open(path) as f:
                data = json.load(f)
            sessions.append({
                "session_id": data.get("session_id", path.stem),
                "message_count": data.get("message_count", 0),
                "saved_at": data.get("saved_at", 0),
                "file": str(path),
            })
        except (json.JSONDecodeError, KeyError):
            continue

    return sessions


def delete_session(session_id: str,
                   input_dir: str | Path = SESSION_DIR) -> bool:
    """Delete a saved session. Returns True if deleted."""
    path = Path(input_dir) / f"{session_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def auto_save(engine: SubphonicsEngine,
              output_dir: str | Path = SESSION_DIR) -> str:
    """Auto-save the current engine session."""
    return save_session(engine.get_session(), output_dir)


def restore_engine(session_id: str,
                   input_dir: str | Path = SESSION_DIR
                   ) -> SubphonicsEngine | None:
    """Restore a SubphonicsEngine from a saved session."""
    session = load_session(session_id, input_dir)
    if session is None:
        return None

    engine = SubphonicsEngine()
    engine.session = session
    return engine


def main() -> None:
    print("Session Persistence Engine")
    print(f"  Session dir: {SESSION_DIR}")

    # Demo: create, save, load
    engine = SubphonicsEngine()
    engine.process_message("hello")
    engine.process_message("status")

    path = save_session(engine.get_session())
    print(f"  Saved: {path}")

    sessions = list_sessions()
    print(f"  Sessions on disk: {len(sessions)}")

    loaded = load_session(engine.get_session().session_id)
    if loaded:
        print(f"  Loaded: {loaded.session_id} ({len(loaded.messages)} messages)")

    print("Done.")


if __name__ == "__main__":
    main()
