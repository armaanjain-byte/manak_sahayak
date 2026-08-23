"""
Structured record fetchers — join semantic candidates back to Postgres facts.

These functions look up structured DB records by `bis_entity_id` only.
They are read-only and must never duplicate structured data elsewhere.
Per architecture.md: RAGFlow is linked to Postgres solely via stable
bis_entity_id; structured facts live in Postgres only.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Laboratory, QCO, Standard


def fetch_standard(session: Session, bis_entity_id: str) -> Optional[Standard]:
    """Return the Standard with this bis_entity_id, or None if not found."""
    return (
        session.query(Standard)
        .filter(Standard.bis_entity_id == bis_entity_id)
        .first()
    )


def fetch_qco(session: Session, bis_entity_id: str) -> Optional[QCO]:
    """Return the QCO with this bis_entity_id, or None if not found."""
    return (
        session.query(QCO)
        .filter(QCO.bis_entity_id == bis_entity_id)
        .first()
    )


def fetch_laboratory(session: Session, bis_entity_id: str) -> Optional[Laboratory]:
    """Return the Laboratory with this bis_entity_id, or None if not found."""
    return (
        session.query(Laboratory)
        .filter(Laboratory.bis_entity_id == bis_entity_id)
        .first()
    )
