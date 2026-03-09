"""Tests for engine.session_persistence — Session 147."""
import pytest
from engine.session_persistence import save_session, load_session, list_sessions
from engine.subphonics import ChatSession, ChatMessage


class TestSessionPersistence:
    def test_save_and_load(self, tmp_path):
        session = ChatSession()
        session.messages.append(ChatMessage(role="user", content="test"))
        path = save_session(session, output_dir=tmp_path)
        assert path
        loaded = load_session(session.session_id, input_dir=tmp_path)
        assert loaded is not None
        assert len(loaded.messages) == 1

    def test_list_sessions_empty(self, tmp_path):
        results = list_sessions(input_dir=tmp_path)
        assert isinstance(results, list)
        assert len(results) == 0
