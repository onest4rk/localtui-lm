from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from src.storage.session import Session, SessionStore, Message


class TestMessage:
    def test_create_message(self):
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is not None

    def test_to_dict(self):
        msg = Message(role="assistant", content="Hi there!", timestamp="2025-01-01T00:00:00")
        d = msg.to_dict()
        assert d["role"] == "assistant"
        assert d["content"] == "Hi there!"
        assert d["timestamp"] == "2025-01-01T00:00:00"

    def test_from_dict(self):
        data = {"role": "user", "content": "Test", "timestamp": "2025-06-01T12:00:00"}
        msg = Message.from_dict(data)
        assert msg.role == "user"
        assert msg.content == "Test"
        assert msg.timestamp == "2025-06-01T12:00:00"


class TestSession:
    def test_create_session(self):
        session = Session(title="Test Session")
        assert session.title == "Test Session"
        assert session.session_id is not None
        assert len(session.messages) == 0

    def test_add_message(self):
        session = Session()
        msg = session.add_message("user", "Hello")
        assert len(session.messages) == 1
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "Hello"

    def test_to_dict(self):
        session = Session(title="Test")
        session.add_message("user", "Hi")
        session.add_message("assistant", "Hello!")
        d = session.to_dict()
        assert d["title"] == "Test"
        assert len(d["messages"]) == 2
        assert d["messages"][0]["role"] == "user"
        assert d["messages"][1]["role"] == "assistant"

    def test_from_dict(self):
        data = {
            "session_id": "test_123",
            "title": "Restored",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T01:00:00",
            "messages": [
                {"role": "user", "content": "Hello", "timestamp": "2025-01-01T00:00:00"},
                {"role": "assistant", "content": "Hi", "timestamp": "2025-01-01T00:00:05"},
            ],
        }
        session = Session.from_dict(data)
        assert session.session_id == "test_123"
        assert session.title == "Restored"
        assert len(session.messages) == 2


class TestSessionStore:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(tmpdir)
            session = Session(title="Save Test")
            session.add_message("user", "Hello")
            session.add_message("assistant", "World")

            store.save(session)
            loaded = store.load(session.session_id)
            assert loaded is not None
            assert loaded.title == "Save Test"
            assert len(loaded.messages) == 2
            assert loaded.messages[0].content == "Hello"

    def test_list_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(tmpdir)
            s1 = Session(title="First")
            s2 = Session(title="Second")
            store.save(s1)
            store.save(s2)

            sessions = store.list_sessions()
            assert len(sessions) >= 2

    def test_delete_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(tmpdir)
            session = Session(title="Delete Me")
            store.save(session)
            assert store.load(session.session_id) is not None

            result = store.delete(session.session_id)
            assert result is True
            assert store.load(session.session_id) is None

    def test_rename_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(tmpdir)
            session = Session(title="Original")
            store.save(session)

            result = store.rename(session.session_id, "Renamed")
            assert result is True

            loaded = store.load(session.session_id)
            assert loaded.title == "Renamed"

    def test_search_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(tmpdir)
            s1 = Session(title="Python Help")
            s1.add_message("user", "How do I use lists?")
            store.save(s1)

            s2 = Session(title="Recipe")
            s2.add_message("user", "Pasta recipe")
            store.save(s2)

            results = store.search("lists")
            assert len(results) >= 1
            assert any("Python Help" in r["title"] for r in results)

            results = store.search("pasta")
            assert len(results) >= 1
