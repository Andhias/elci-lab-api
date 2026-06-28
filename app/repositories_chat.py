from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models_chat import ChatMessageModel, ChatSessionModel
from app.schemas.chat import ChatSessionSummary, ChatTurn


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, title: str | None, user_id: str = 'demo-user') -> ChatSessionModel:
        session = ChatSessionModel(title=title, user_id=user_id)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: str) -> ChatSessionModel | None:
        return self.db.get(ChatSessionModel, session_id)

    def list_sessions(self, limit: int = 20) -> list[ChatSessionSummary]:
        stmt = select(ChatSessionModel).order_by(desc(ChatSessionModel.updated_at)).limit(limit)
        sessions = list(self.db.scalars(stmt))
        summaries: list[ChatSessionSummary] = []
        for session in sessions:
            messages = self.list_messages(session.id)
            last_message_preview = messages[-1].content[:80] if messages else None
            updated_at = session.updated_at.isoformat() if isinstance(session.updated_at, datetime) else None
            summaries.append(
                ChatSessionSummary(
                    id=session.id,
                    title=session.title,
                    updated_at=updated_at,
                    last_message_preview=last_message_preview,
                    message_count=len(messages),
                )
            )
        return summaries

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        confidence: str | None = None,
        match_type: str | None = None,
        trace_json: dict | None = None,
    ) -> ChatMessageModel:
        message = ChatMessageModel(
            session_id=session_id,
            role=role,
            content=content,
            answer_confidence=confidence,
            answer_match_type=match_type,
            trace_json=trace_json or {},
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def list_messages(self, session_id: str) -> list[ChatMessageModel]:
        stmt = select(ChatMessageModel).where(ChatMessageModel.session_id == session_id).order_by(ChatMessageModel.created_at)
        return list(self.db.scalars(stmt))


def message_models_to_turns(messages: Iterable[ChatMessageModel]) -> list[ChatTurn]:
    turns: list[ChatTurn] = []
    for item in messages:
        trace_json = item.trace_json or {}
        citation_count = trace_json.get('citation_count', 0)
        turns.append(
            ChatTurn(
                role=item.role,
                content=item.content,
                match_type=item.answer_match_type,
                confidence=item.answer_confidence,
                citation_count=citation_count,
            )
        )
    return turns
