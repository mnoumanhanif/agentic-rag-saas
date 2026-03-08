"""Conversation and message management API routes."""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from rag_system.auth.dependencies import get_current_user
from rag_system.database.engine import get_db
from rag_system.database.models import Conversation, Message, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


# ── Schemas ────────────────────────────────────────────────────────────────

class ConversationCreateRequest(BaseModel):
    title: str = Field("New Conversation", max_length=255)
    knowledge_base_id: Optional[str] = None


class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    is_pinned: Optional[bool] = None


class MessageSchema(BaseModel):
    id: str
    role: str
    content: str
    sources: Optional[list] = None
    query_analysis: Optional[dict] = None
    reflection: Optional[dict] = None
    steps: Optional[list] = None
    tokens_used: int = 0
    latency_ms: int = 0
    created_at: str


class ConversationResponse(BaseModel):
    id: str
    title: str
    knowledge_base_id: Optional[str]
    is_pinned: bool
    created_at: str
    updated_at: str
    message_count: int = 0


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int


class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageSchema]


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    body: ConversationCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new conversation."""
    conv = Conversation(
        user_id=user.id,
        title=body.title,
        knowledge_base_id=body.knowledge_base_id,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return _conv_to_response(conv)


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all conversations for the current user."""
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return ConversationListResponse(
        conversations=[_conv_to_response(c) for c in convs],
        total=len(convs),
    )


@router.get("/{conv_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conv_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a conversation with all its messages."""
    conv = _get_user_conv(conv_id, user, db)
    return _conv_to_detail_response(conv)


@router.patch("/{conv_id}", response_model=ConversationResponse)
def update_conversation(
    conv_id: str,
    body: ConversationUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a conversation title or pin status."""
    conv = _get_user_conv(conv_id, user, db)
    if body.title is not None:
        conv.title = body.title
    if body.is_pinned is not None:
        conv.is_pinned = body.is_pinned
    db.commit()
    db.refresh(conv)
    return _conv_to_response(conv)


@router.delete("/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conv_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a conversation and all its messages."""
    conv = _get_user_conv(conv_id, user, db)
    db.delete(conv)
    db.commit()


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_user_conv(conv_id: str, user: User, db: Session) -> Conversation:
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == user.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


def _conv_to_response(conv: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        knowledge_base_id=conv.knowledge_base_id,
        is_pinned=conv.is_pinned,
        created_at=conv.created_at.isoformat() if conv.created_at else "",
        updated_at=conv.updated_at.isoformat() if conv.updated_at else "",
        message_count=len(conv.messages) if conv.messages else 0,
    )


def _conv_to_detail_response(conv: Conversation) -> ConversationDetailResponse:
    return ConversationDetailResponse(
        id=conv.id,
        title=conv.title,
        knowledge_base_id=conv.knowledge_base_id,
        is_pinned=conv.is_pinned,
        created_at=conv.created_at.isoformat() if conv.created_at else "",
        updated_at=conv.updated_at.isoformat() if conv.updated_at else "",
        message_count=len(conv.messages) if conv.messages else 0,
        messages=[_msg_to_schema(m) for m in (conv.messages or [])],
    )


def _msg_to_schema(m: Message) -> MessageSchema:
    return MessageSchema(
        id=m.id,
        role=m.role,
        content=m.content,
        sources=json.loads(m.sources) if m.sources else None,
        query_analysis=json.loads(m.query_analysis) if m.query_analysis else None,
        reflection=json.loads(m.reflection) if m.reflection else None,
        steps=json.loads(m.steps) if m.steps else None,
        tokens_used=m.tokens_used,
        latency_ms=m.latency_ms,
        created_at=m.created_at.isoformat() if m.created_at else "",
    )
