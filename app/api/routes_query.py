"""
POST /query — primary entry point.

Flow:
    request -> OrchestrationRouter -> WorkflowResult
            -> ResponseBuilder     -> JSON response
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.generation.response_builder import build_response
from app.orchestration.router import OrchestrationRouter

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str


class EvidenceItem(BaseModel):
    source_id: str
    source_type: str
    content: str
    authoritative: bool


class QueryResponse(BaseModel):
    state: str
    explanation: str
    evidence: list[EvidenceItem] = []
    clarification_question: str | None = None
    clarification_options: list[str] | None = None
    handoff_url: str | None = None
    handoff_action_type: str | None = None


# ---------------------------------------------------------------------------
# Dependency — RAGFlow client (injectable for tests)
# ---------------------------------------------------------------------------

def get_ragflow_client() -> Any:
    """
    Returns the RAGFlow client.
    Swappable via FastAPI dependency override in tests.
    """
    from app.retrieval.ragflow_client import RagflowClient
    return RagflowClient()


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post("/query", response_model=QueryResponse)
async def query(
    body: QueryRequest,
    db: Session = Depends(get_db),
    ragflow_client: Any = Depends(get_ragflow_client),
) -> QueryResponse:
    """
    Primary reasoning endpoint.

    Accepts a natural-language query, routes it through the orchestration
    layer and returns a structured, evidence-backed response.
    """
    if not body.query.strip():
        raise HTTPException(status_code=422, detail="query must not be empty")

    try:
        orch = OrchestrationRouter(session=db, ragflow_client=ragflow_client)
        result = await orch.route(body.query)
    except Exception as exc:
        logger.error("Orchestration error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal reasoning error") from exc

    try:
        explanation = await build_response(result)
    except Exception as exc:
        logger.error("Response builder error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal generation error") from exc

    evidence = [
        EvidenceItem(
            source_id=e.source_id,
            source_type=e.source_type,
            content=e.content,
            authoritative=e.authoritative,
        )
        for e in (result.evidence or [])
    ]

    clarification_question: str | None = None
    clarification_options: list[str] | None = None
    if result.clarification:
        clarification_question = result.clarification.question
        clarification_options = result.clarification.options or None

    handoff_url: str | None = None
    handoff_action_type: str | None = None
    if result.action:
        handoff_url = result.action.destination_url
        handoff_action_type = result.action.action_type

    return QueryResponse(
        state=result.state.value,
        explanation=explanation,
        evidence=evidence,
        clarification_question=clarification_question,
        clarification_options=clarification_options,
        handoff_url=handoff_url,
        handoff_action_type=handoff_action_type,
    )
