"""Document management API routes."""

import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from rag_system.auth.dependencies import get_current_user
from rag_system.database.engine import get_db
from rag_system.database.models import Document, KnowledgeBase, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-bases/{kb_id}/documents", tags=["documents"])


# ── Schemas ────────────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    mime_type: str
    chunk_count: int
    status: str
    error_message: Optional[str] = None
    uploaded_at: str
    indexed_at: Optional[str] = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a document to a knowledge base."""
    kb = _get_user_kb(kb_id, user, db)

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".pdf",):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    max_size = 50 * 1024 * 1024  # 50 MB
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail="File exceeds 50MB limit")

    if not content[:5] == b"%PDF-":
        raise HTTPException(status_code=400, detail="Not a valid PDF file")

    doc = Document(
        knowledge_base_id=kb.id,
        filename=file.filename,
        file_size=len(content),
        status="pending",
    )
    db.add(doc)
    kb.document_count = kb.document_count + 1
    db.commit()
    db.refresh(doc)

    # Save file for background processing
    upload_dir = os.path.join("uploads", kb.id)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{doc.id}.pdf")
    with open(file_path, "wb") as f:
        f.write(content)

    logger.info("Document %s uploaded to KB %s", doc.id, kb.id)
    return _doc_to_response(doc)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    kb_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all documents in a knowledge base."""
    kb = _get_user_kb(kb_id, user, db)
    docs = db.query(Document).filter(Document.knowledge_base_id == kb.id).all()
    return DocumentListResponse(
        documents=[_doc_to_response(d) for d in docs],
        total=len(docs),
    )


@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(
    kb_id: str,
    doc_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get document details."""
    _get_user_kb(kb_id, user, db)
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.knowledge_base_id == kb_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_to_response(doc)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    kb_id: str,
    doc_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document from a knowledge base."""
    kb = _get_user_kb(kb_id, user, db)
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.knowledge_base_id == kb_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove file from disk
    file_path = os.path.join("uploads", kb.id, f"{doc.id}.pdf")
    if os.path.exists(file_path):
        os.remove(file_path)

    kb.document_count = max(0, kb.document_count - 1)
    db.delete(doc)
    db.commit()
    logger.info("Document %s deleted from KB %s", doc_id, kb_id)


@router.post("/{doc_id}/reindex", response_model=DocumentResponse)
def reindex_document(
    kb_id: str,
    doc_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-index a document (reset status to trigger re-processing)."""
    _get_user_kb(kb_id, user, db)
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.knowledge_base_id == kb_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.status = "pending"
    doc.chunk_count = 0
    doc.indexed_at = None
    doc.error_message = None
    db.commit()
    db.refresh(doc)

    logger.info("Document %s queued for re-indexing", doc_id)
    return _doc_to_response(doc)


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_user_kb(kb_id: str, user: User, db: Session) -> KnowledgeBase:
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.owner_id == user.id,
    ).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


def _doc_to_response(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        chunk_count=doc.chunk_count,
        status=doc.status,
        error_message=doc.error_message,
        uploaded_at=doc.uploaded_at.isoformat() if doc.uploaded_at else "",
        indexed_at=doc.indexed_at.isoformat() if doc.indexed_at else None,
    )
