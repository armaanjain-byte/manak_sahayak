"""
Debug-only workflow endpoints.

These bypass the orchestration intent classifier and call a specific
workflow directly. Intended for demo debugging and benchmark runs only —
NOT part of the public API surface.

All routes are prefixed with /debug and are clearly documented as such.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.generation.response_builder import build_response
from app.workflows.workflow1_standard_qco import Workflow1StandardQCO
from app.workflows.workflow2_lab import Workflow2Lab
from app.workflows.workflow3_hallmarking import Workflow3Hallmarking

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["debug"])


# ---------------------------------------------------------------------------
# Shared schemas
# ---------------------------------------------------------------------------

class DebugQueryRequest(BaseModel):
    query: str


class DebugQueryResponse(BaseModel):
    workflow: str
    state: str
    explanation: str
    raw_decision: dict[str, object] | None = None
    evidence_count: int = 0


# ---------------------------------------------------------------------------
# Dependency — same pattern as routes_query so tests can override it
# ---------------------------------------------------------------------------

def get_ragflow_client() -> Any:
    from app.retrieval.ragflow_client import RagflowClient
    return RagflowClient()


# ---------------------------------------------------------------------------
# Debug routes
# ---------------------------------------------------------------------------

async def _run_debug(
    workflow_name: str,
    body: DebugQueryRequest,
    db: Session,
    ragflow_client: Any,
) -> DebugQueryResponse:
    """Shared debug runner — instantiate the named workflow and run."""
    try:
        wf: Workflow1StandardQCO | Workflow2Lab | Workflow3Hallmarking
        if workflow_name == "workflow1":
            wf = Workflow1StandardQCO(session=db, ragflow_client=ragflow_client)
        elif workflow_name == "workflow2":
            wf = Workflow2Lab(session=db, ragflow_client=ragflow_client)
        elif workflow_name == "workflow3":
            wf = Workflow3Hallmarking(session=db)
        else:
            raise ValueError(f"Unknown workflow: {workflow_name}")

        result = await wf.run(body.query)
    except Exception as exc:
        logger.error("Debug workflow error [%s]: %s", workflow_name, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Workflow error: {exc}") from exc

    try:
        explanation = await build_response(result)
    except Exception as exc:
        logger.error("Debug response builder error: %s", exc, exc_info=True)
        explanation = f"[Response builder error: {exc}]"

    raw_decision = result.decision.model_dump(exclude_none=True) if result.decision else None

    return DebugQueryResponse(
        workflow=workflow_name,
        state=result.state.value,
        explanation=explanation,
        raw_decision=raw_decision,
        evidence_count=len(result.evidence or []),
    )


@router.post("/workflow1", response_model=DebugQueryResponse, summary="[DEBUG] Direct Workflow 1 (Standard/QCO)")
async def debug_workflow1(
    body: DebugQueryRequest,
    db: Session = Depends(get_db),
    ragflow_client: Any = Depends(get_ragflow_client),
) -> DebugQueryResponse:
    """
    **Debug only.** Calls Workflow 1 (Standard/QCO) directly,
    bypassing intent classification.
    """
    return await _run_debug("workflow1", body, db, ragflow_client)


@router.post("/workflow2", response_model=DebugQueryResponse, summary="[DEBUG] Direct Workflow 2 (Lab)")
async def debug_workflow2(
    body: DebugQueryRequest,
    db: Session = Depends(get_db),
    ragflow_client: Any = Depends(get_ragflow_client),
) -> DebugQueryResponse:
    """
    **Debug only.** Calls Workflow 2 (Laboratory discovery) directly,
    bypassing intent classification.
    """
    return await _run_debug("workflow2", body, db, ragflow_client)


@router.post("/workflow3", response_model=DebugQueryResponse, summary="[DEBUG] Direct Workflow 3 (Hallmarking)")
async def debug_workflow3(
    body: DebugQueryRequest,
    db: Session = Depends(get_db),
    ragflow_client: Any = Depends(get_ragflow_client),
) -> DebugQueryResponse:
    """
    **Debug only.** Calls Workflow 3 (Hallmarking/HUID) directly,
    bypassing intent classification.
    """
    return await _run_debug("workflow3", body, db, ragflow_client)
