"""Admin panel and analytics API routes."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from rag_system.auth.dependencies import get_current_user, require_admin
from rag_system.database.engine import get_db
from rag_system.database.models import (
    AnalyticsEvent,
    Conversation,
    Document,
    KnowledgeBase,
    Message,
    User,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Schemas ────────────────────────────────────────────────────────────────

class SystemMetrics(BaseModel):
    total_users: int
    active_users: int
    total_knowledge_bases: int
    total_documents: int
    total_conversations: int
    total_messages: int
    total_queries_24h: int
    avg_latency_ms: float
    total_tokens_used: int
    error_rate: float


class UserSummary(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str
    knowledge_base_count: int
    conversation_count: int


class UserListResponse(BaseModel):
    users: List[UserSummary]
    total: int


class QueryAnalytics(BaseModel):
    total_queries: int
    avg_latency_ms: float
    total_tokens: int
    queries_by_day: List[dict]
    error_count: int


# ── Admin endpoints ────────────────────────────────────────────────────────

@router.get("/metrics", response_model=SystemMetrics)
def get_system_metrics(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Get system-wide metrics (admin only)."""
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)

    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
    total_kbs = db.query(func.count(KnowledgeBase.id)).scalar() or 0
    total_docs = db.query(func.count(Document.id)).scalar() or 0
    total_convs = db.query(func.count(Conversation.id)).scalar() or 0
    total_msgs = db.query(func.count(Message.id)).scalar() or 0

    queries_24h = (
        db.query(func.count(AnalyticsEvent.id))
        .filter(AnalyticsEvent.event_type == "query", AnalyticsEvent.created_at >= day_ago)
        .scalar() or 0
    )

    avg_latency = (
        db.query(func.avg(AnalyticsEvent.latency_ms))
        .filter(AnalyticsEvent.event_type == "query")
        .scalar() or 0.0
    )

    total_tokens = (
        db.query(func.sum(AnalyticsEvent.tokens_used))
        .filter(AnalyticsEvent.event_type == "query")
        .scalar() or 0
    )

    total_events = db.query(func.count(AnalyticsEvent.id)).scalar() or 1
    error_count = db.query(func.count(AnalyticsEvent.id)).filter(
        AnalyticsEvent.success.is_(False)
    ).scalar() or 0
    error_rate = error_count / max(total_events, 1)

    return SystemMetrics(
        total_users=total_users,
        active_users=active_users,
        total_knowledge_bases=total_kbs,
        total_documents=total_docs,
        total_conversations=total_convs,
        total_messages=total_msgs,
        total_queries_24h=queries_24h,
        avg_latency_ms=round(float(avg_latency), 2),
        total_tokens_used=total_tokens,
        error_rate=round(error_rate, 4),
    )


@router.get("/users", response_model=UserListResponse)
def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """List all users (admin only)."""
    users = db.query(User).all()
    summaries = []
    for u in users:
        kb_count = db.query(func.count(KnowledgeBase.id)).filter(KnowledgeBase.owner_id == u.id).scalar() or 0
        conv_count = db.query(func.count(Conversation.id)).filter(Conversation.user_id == u.id).scalar() or 0
        summaries.append(UserSummary(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at.isoformat() if u.created_at else "",
            knowledge_base_count=kb_count,
            conversation_count=conv_count,
        ))
    return UserListResponse(users=summaries, total=len(summaries))


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    role: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update a user's role (admin only)."""
    if role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = role
    db.commit()
    return {"message": f"User {user_id} role updated to {role}"}


@router.patch("/users/{user_id}/toggle-active")
def toggle_user_active(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Toggle a user's active status (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not user.is_active
    db.commit()
    return {"message": f"User {user_id} active status: {user.is_active}"}


# ── Analytics endpoints (authenticated user) ──────────────────────────────

analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


@analytics_router.get("/queries", response_model=QueryAnalytics)
def get_query_analytics(
    days: int = 7,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get query analytics for the current user."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    base_query = db.query(AnalyticsEvent).filter(
        AnalyticsEvent.user_id == user.id,
        AnalyticsEvent.event_type == "query",
        AnalyticsEvent.created_at >= since,
    )

    total = base_query.count()
    avg_latency = db.query(func.avg(AnalyticsEvent.latency_ms)).filter(
        AnalyticsEvent.user_id == user.id,
        AnalyticsEvent.event_type == "query",
        AnalyticsEvent.created_at >= since,
    ).scalar() or 0.0

    total_tokens = db.query(func.sum(AnalyticsEvent.tokens_used)).filter(
        AnalyticsEvent.user_id == user.id,
        AnalyticsEvent.event_type == "query",
        AnalyticsEvent.created_at >= since,
    ).scalar() or 0

    error_count = base_query.filter(AnalyticsEvent.success.is_(False)).count()

    # Group by day for chart
    queries_by_day = []
    for i in range(days):
        day = datetime.now(timezone.utc) - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = db.query(func.count(AnalyticsEvent.id)).filter(
            AnalyticsEvent.user_id == user.id,
            AnalyticsEvent.event_type == "query",
            AnalyticsEvent.created_at >= day_start,
            AnalyticsEvent.created_at < day_end,
        ).scalar() or 0
        queries_by_day.append({"date": day_start.strftime("%Y-%m-%d"), "count": count})

    return QueryAnalytics(
        total_queries=total,
        avg_latency_ms=round(float(avg_latency), 2),
        total_tokens=total_tokens,
        queries_by_day=list(reversed(queries_by_day)),
        error_count=error_count,
    )
