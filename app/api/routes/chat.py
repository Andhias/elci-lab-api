from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.repositories_chat import ChatRepository, message_models_to_turns
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionListResponse,
    ChatSessionResponse,
)
from app.services.llm_service import call_llm

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/sessions", response_model=ChatSessionListResponse)
def list_sessions(db: Session = Depends(get_db)) -> ChatSessionListResponse:
    repo = ChatRepository(db)
    return ChatSessionListResponse(sessions=repo.list_sessions())


@router.post("/sessions", response_model=ChatSessionResponse)
def create_session(
    payload: ChatSessionCreateRequest,
    db: Session = Depends(get_db),
) -> ChatSessionResponse:
    repo = ChatRepository(db)
    session = repo.create_session(payload.title)
    return ChatSessionResponse(id=session.id, title=session.title, history=[])


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
def get_session(session_id: str, db: Session = Depends(get_db)) -> ChatSessionResponse:
    repo = ChatRepository(db)
    session = repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    history = message_models_to_turns(repo.list_messages(session_id))
    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        history=history,
    )


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
def create_message(
    session_id: str,
    payload: ChatMessageRequest,
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    repo = ChatRepository(db)
    session = repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Save user message
    repo.add_message(
        session_id=session_id,
        role="user",
        content=payload.message,
    )

    # Build history for LLM context
    history = message_models_to_turns(repo.list_messages(session_id))
    history_dicts = [
        {"role": turn.role, "content": turn.content}
        for turn in history[:-1]  # exclude the user message we just added
    ]

    # Call LLM
    answer = call_llm(payload.message, history=history_dicts)

    # Save assistant response
    assistant_message = repo.add_message(
        session_id=session_id,
        role="assistant",
        content=answer.issue_summary,
        confidence=answer.confidence,
        match_type=answer.match_type,
        trace_json={
            "citation_count": len(answer.citations),
            "provider": "llm_service",
        },
    )

    history = message_models_to_turns(repo.list_messages(session_id))

    return ChatMessageResponse(
        message_id=assistant_message.id,
        session_id=session_id,
        answer=answer,
        history=history,
    )
