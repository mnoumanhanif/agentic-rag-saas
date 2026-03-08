"""Knowledge Base management API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional

from rag_system.auth.dependencies import get_current_user
from rag_system.database.engine import get_db
from rag_system.database.models import KnowledgeBase, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


# ── Schemas ────────────────────────────────────────────────────────────────

class KBCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("", max_length=2000)


class KBUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class KBResponse(BaseModel):
    id: str
    name: str
    description: str
    document_count: int
    total_chunks: int
    status: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class KBListResponse(BaseModel):
    knowledge_bases: List[KBResponse]
    total: int


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("", response_model=KBResponse, status_code=status.HTTP_201_CREATED)
def create_kb(body: KBCreateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new knowledge base."""
    kb = KnowledgeBase(name=body.name, description=body.description, owner_id=user.id)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    logger.info("Knowledge base created: %s by user %s", kb.id, user.id)
    return _kb_to_response(kb)


@router.get("", response_model=KBListResponse)
def list_kbs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all knowledge bases owned by the current user."""
    kbs = db.query(KnowledgeBase).filter(KnowledgeBase.owner_id == user.id).all()
    return KBListResponse(
        knowledge_bases=[_kb_to_response(kb) for kb in kbs],
        total=len(kbs),
    )


@router.get("/{kb_id}", response_model=KBResponse)
def get_kb(kb_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get a specific knowledge base."""
    kb = _get_user_kb(kb_id, user, db)
    return _kb_to_response(kb)


@router.patch("/{kb_id}", response_model=KBResponse)
def update_kb(kb_id: str, body: KBUpdateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a knowledge base."""
    kb = _get_user_kb(kb_id, user, db)
    if body.name is not None:
        kb.name = body.name
    if body.description is not None:
        kb.description = body.description
    db.commit()
    db.refresh(kb)
    return _kb_to_response(kb)


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kb(kb_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a knowledge base and all its documents."""
    kb = _get_user_kb(kb_id, user, db)
    db.delete(kb)
    db.commit()
    logger.info("Knowledge base deleted: %s by user %s", kb_id, user.id)


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_user_kb(kb_id: str, user: User, db: Session) -> KnowledgeBase:
    """Fetch a KB ensuring it belongs to the current user."""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.owner_id == user.id,
    ).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


def _kb_to_response(kb: KnowledgeBase) -> KBResponse:
    return KBResponse(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        document_count=kb.document_count,
        total_chunks=kb.total_chunks,
        status=kb.status,
        created_at=kb.created_at.isoformat() if kb.created_at else "",
        updated_at=kb.updated_at.isoformat() if kb.updated_at else "",
    )
