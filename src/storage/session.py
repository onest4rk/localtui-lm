from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class Message:
    def __init__(self, role: str, content: str, timestamp: Optional[str] = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp"),
        )


class Session:
    def __init__(self, title: str = "Untitled", session_id: Optional[str] = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S%f")
        self.title = title
        self.messages: list[Message] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

    def add_message(self, role: str, content: str) -> Message:
        msg = Message(role=role, content=content)
        self.messages.append(msg)
        self.updated_at = datetime.now().isoformat()
        return msg

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [m.to_dict() for m in self.messages],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        session = cls(
            title=data.get("title", "Untitled"),
            session_id=data.get("session_id"),
        )
        session.created_at = data.get("created_at", session.created_at)
        session.updated_at = data.get("updated_at", session.updated_at)
        session.messages = [Message.from_dict(m) for m in data.get("messages", [])]
        return session


class SessionStore:
    def __init__(self, save_dir: str):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def save(self, session: Session) -> Path:
        path = self.save_dir / f"{session.session_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
        return path

    def load(self, session_id: str) -> Optional[Session]:
        path = self.save_dir / f"{session_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Session.from_dict(data)

    def delete(self, session_id: str) -> bool:
        path = self.save_dir / f"{session_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def list_sessions(self) -> list[dict]:
        sessions = []
        for path in sorted(self.save_dir.glob("*.json"), reverse=True):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append({
                    "session_id": data.get("session_id", path.stem),
                    "title": data.get("title", "Untitled"),
                    "updated_at": data.get("updated_at", ""),
                    "message_count": len(data.get("messages", [])),
                })
            except (json.JSONDecodeError, OSError):
                continue
        return sessions

    def search(self, query: str) -> list[dict]:
        query = query.lower()
        results = []
        for session_info in self.list_sessions():
            session = self.load(session_info["session_id"])
            if session is None:
                continue
            content = " ".join(m.content.lower() for m in session.messages)
            if query in content or query in session.title.lower():
                results.append(session_info)
        return results

    def rename(self, session_id: str, new_title: str) -> bool:
        session = self.load(session_id)
        if session is None:
            return False
        session.title = new_title
        self.save(session)
        return True
