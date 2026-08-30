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

from app.actions.router import UnknownDestinationError, resolve_action
from app.db.session import get_db
from app.generation.response_builder import build_response
from app.orchestration.router import OrchestrationRouter

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    query: str = Field(..., max_length=2000)


class EvidenceItem(BaseModel):
    source_id: str
    source_type: str
    content: str
    authoritative: bool


class DecisionItem(BaseModel):
    standard: str | None = None
    mandatory: bool | None = None
    basis: str | None = None
    effective_from: str | None = None
    pathway: str | None = None
    confidence: str


class QueryResponse(BaseModel):
    state: str
    explanation: str
    decision: DecisionItem | None = None
    confidence: str | None = None
    evidence: list[EvidenceItem] = []
    clarification_question: str | None = None
    clarification_options: list[str] | None = None
    handoff_url: str | None = None
    handoff_action_type: str | None = None
    handoff_disclaimer: str | None = None


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
    handoff_disclaimer: str | None = None
    if result.action:
        try:
            resolved_action = resolve_action(result.action)
        except UnknownDestinationError as exc:
            logger.error("Unsafe action destination: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail="Internal action routing error") from exc

        handoff_url = resolved_action.destination_url
        handoff_action_type = resolved_action.action_type
        handoff_disclaimer = resolved_action.disclaimer

    decision: DecisionItem | None = None
    confidence: str | None = None
    if result.decision:
        decision = DecisionItem(
            standard=result.decision.standard,
            mandatory=result.decision.mandatory,
            basis=result.decision.basis,
            effective_from=result.decision.effective_from,
            pathway=result.decision.pathway,
            confidence=result.decision.confidence.value,
        )
        confidence = result.decision.confidence.value

    return QueryResponse(
        state=result.state.value,
        explanation=explanation,
        decision=decision,
        confidence=confidence,
        evidence=evidence,
        clarification_question=clarification_question,
        clarification_options=clarification_options,
        handoff_url=handoff_url,
        handoff_action_type=handoff_action_type,
        handoff_disclaimer=handoff_disclaimer,
    )
