"""
Integration tests for the API layer.

Uses FastAPI's TestClient. The orchestration layer and generation layer
are mocked — these tests verify API wiring, request/response shapes,
error handling, and that debug endpoints bypass the main classifier.
"""
from __future__ import annotations

from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.actions.destinations import BIS_MAIN_URL
from app.core.entities import (
    Action,
    ClarificationRequest,
    DecisionObject,
    Evidence,
    Confidence,
)
from app.core.states import ResponseState
from app.db.session import Base, get_db
from app.main import app
from app.workflows.base import WorkflowResult


# ---------------------------------------------------------------------------
# Fixtures — in-memory DB + mocked ragflow
# ---------------------------------------------------------------------------

@pytest.fixture(name="db_session")
def fixture_db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(bind=engine)



@pytest.fixture(name="client")
def fixture_client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient with DB and ragflow dependencies overridden."""
    mock_ragflow = MagicMock()

    app.dependency_overrides[get_db] = lambda: db_session

    # Override ragflow in both routers
    from app.api.routes_query import get_ragflow_client as q_ragflow
    from app.api.routes_workflows import get_ragflow_client as wf_ragflow
    app.dependency_overrides[q_ragflow] = lambda: mock_ragflow
    app.dependency_overrides[wf_ragflow] = lambda: mock_ragflow

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper — build a WorkflowResult for a given state
# ---------------------------------------------------------------------------

def _answered_result() -> WorkflowResult:
    return WorkflowResult(
        state=ResponseState.ANSWERED,
        decision=DecisionObject(
            standard="IS 1234",
            mandatory=True,
            effective_from="2023-01-01",
            confidence=Confidence.HIGH,
        ),
        evidence=[
            Evidence(
                source_id="ev1",
                source_type="qco_gazette",
                content="IS 1234 is mandatory",
                authoritative=True,
            )
        ],
    )


def _clarification_result() -> WorkflowResult:
    return WorkflowResult(
        state=ResponseState.CLARIFICATION,
        clarification=ClarificationRequest(
            question="What type of product?",
            options=["Toy", "Electrical"],
        ),
    )


def _not_found_result() -> WorkflowResult:
    return WorkflowResult(state=ResponseState.NOT_FOUND)


def _handoff_result() -> WorkflowResult:
    return WorkflowResult(
        state=ResponseState.HANDOFF,
        action=Action(action_type="general_bis_handoff", destination_url=BIS_MAIN_URL),
    )


def _unsafe_handoff_result() -> WorkflowResult:
    return WorkflowResult(
        state=ResponseState.HANDOFF,
        action=Action(
            action_type="general_bis_handoff",
            destination_url="https://unapproved.example.com/",
        ),
    )


def _conflict_result() -> WorkflowResult:
    return WorkflowResult(
        state=ResponseState.CONFLICT,
        evidence=[
            Evidence(source_id="a", source_type="t", content="A says mandatory", authoritative=True),
            Evidence(source_id="b", source_type="t", content="B says not mandatory", authoritative=True),
        ],
    )


# ---------------------------------------------------------------------------
# POST /query — correct shape per state
# ---------------------------------------------------------------------------

@patch("app.api.routes_query.OrchestrationRouter")
@patch("app.api.routes_query.build_response", new_callable=AsyncMock)
def test_query_answered_shape(mock_build: AsyncMock, mock_orch_class: MagicMock, client: TestClient) -> None:
    """ANSWERED: response has state, explanation, decision, confidence, evidence."""
    mock_orch = AsyncMock()
    mock_orch.route.return_value = _answered_result()
    mock_orch_class.return_value = mock_orch
    mock_build.return_value = "IS 1234 is mandatory from 2023-01-01."

    resp = client.post("/query", json={"query": "is cement regulated?"})
    assert resp.status_code == 200

    body = resp.json()
    assert body["state"] == "ANSWERED"
    assert body["explanation"] == "IS 1234 is mandatory from 2023-01-01."
    assert body["decision"] == {
        "standard": "IS 1234",
        "mandatory": True,
        "basis": None,
        "effective_from": "2023-01-01",
        "pathway": None,
        "confidence": "HIGH",
    }
    assert body["confidence"] == "HIGH"
    assert len(body["evidence"]) == 1
    assert body["evidence"][0]["source_id"] == "ev1"
    assert body["clarification_question"] is None
    assert body["handoff_url"] is None


@patch("app.api.routes_query.OrchestrationRouter")
@patch("app.api.routes_query.build_response", new_callable=AsyncMock)
def test_query_clarification_shape(mock_build: AsyncMock, mock_orch_class: MagicMock, client: TestClient) -> None:
    """CLARIFICATION: response has clarification_question and options."""
    mock_orch = AsyncMock()
    mock_orch.route.return_value = _clarification_result()
    mock_orch_class.return_value = mock_orch
    mock_build.return_value = "Could you tell me what type of product?"

    resp = client.post("/query", json={"query": "do I need certification?"})
    assert resp.status_code == 200

    body = resp.json()
    assert body["state"] == "CLARIFICATION"
    assert body["decision"] is None
    assert body["confidence"] is None
    assert body["clarification_question"] == "What type of product?"
    assert body["clarification_options"] == ["Toy", "Electrical"]
    assert body["handoff_url"] is None


@patch("app.api.routes_query.OrchestrationRouter")
@patch("app.api.routes_query.build_response", new_callable=AsyncMock)
def test_query_not_found_shape(mock_build: AsyncMock, mock_orch_class: MagicMock, client: TestClient) -> None:
    """NOT_FOUND: response has state, explanation, empty evidence."""
    mock_orch = AsyncMock()
    mock_orch.route.return_value = _not_found_result()
    mock_orch_class.return_value = mock_orch
    mock_build.return_value = "Could not find relevant standard."

    resp = client.post("/query", json={"query": "unicorn certification"})
    assert resp.status_code == 200

    body = resp.json()
    assert body["state"] == "NOT_FOUND"
    assert body["decision"] is None
    assert body["confidence"] is None
    assert body["evidence"] == []
    assert body["handoff_url"] is None


@patch("app.api.routes_query.OrchestrationRouter")
@patch("app.api.routes_query.build_response", new_callable=AsyncMock)
def test_query_handoff_shape(mock_build: AsyncMock, mock_orch_class: MagicMock, client: TestClient) -> None:
    """HANDOFF: response includes handoff_url and action_type."""
    mock_orch = AsyncMock()
    mock_orch.route.return_value = _handoff_result()
    mock_orch_class.return_value = mock_orch
    mock_build.return_value = "Handing off to BIS."

    resp = client.post("/query", json={"query": "I have a complaint"})
    assert resp.status_code == 200

    body = resp.json()
    assert body["state"] == "HANDOFF"
    assert body["decision"] is None
    assert body["confidence"] is None
    assert body["handoff_url"] == BIS_MAIN_URL
    assert body["handoff_action_type"] == "general_bis_handoff"
    assert "official Bureau of Indian Standards" in body["handoff_disclaimer"]


@patch("app.api.routes_query.OrchestrationRouter")
@patch("app.api.routes_query.build_response", new_callable=AsyncMock)
def test_query_conflict_shape(mock_build: AsyncMock, mock_orch_class: MagicMock, client: TestClient) -> None:
    """CONFLICT: response has state and evidence from both conflicting sources."""
    mock_orch = AsyncMock()
    mock_orch.route.return_value = _conflict_result()
    mock_orch_class.return_value = mock_orch
    mock_build.return_value = "Conflicting evidence found."

    resp = client.post("/query", json={"query": "is product X mandatory?"})
    assert resp.status_code == 200

    body = resp.json()
    assert body["state"] == "CONFLICT"
    assert body["decision"] is None
    assert body["confidence"] is None
    assert len(body["evidence"]) == 2


# ---------------------------------------------------------------------------
# POST /query — error cases
# ---------------------------------------------------------------------------

def test_query_empty_string_422(client: TestClient) -> None:
    """Empty query string returns 422."""
    resp = client.post("/query", json={"query": "   "})
    assert resp.status_code == 422


def test_query_missing_field_422(client: TestClient) -> None:
    """Missing query field returns 422."""
    resp = client.post("/query", json={})
    assert resp.status_code == 422


def test_query_wrong_type_422(client: TestClient) -> None:
    """Wrong type for query field returns 422."""
    resp = client.post("/query", json={"query": 123})
    assert resp.status_code == 422


@patch("app.api.routes_query.OrchestrationRouter")
def test_query_orchestration_error_500(mock_orch_class: MagicMock, client: TestClient) -> None:
    """Orchestration crash returns 500 with clean message, no stack trace."""
    mock_orch = AsyncMock()
    mock_orch.route.side_effect = RuntimeError("DB connection failed")
    mock_orch_class.return_value = mock_orch

    resp = client.post("/query", json={"query": "is steel regulated?"})
    assert resp.status_code == 500
    body = resp.json()
    # Must not leak internals
    assert "DB connection failed" not in body["detail"]
    assert "Internal" in body["detail"]


@patch("app.api.routes_query.OrchestrationRouter")
@patch("app.api.routes_query.build_response", new_callable=AsyncMock)
def test_query_rejects_unknown_handoff_destination(
    mock_build: AsyncMock,
    mock_orch_class: MagicMock,
    client: TestClient,
) -> None:
    """HANDOFF actions must use a known official destination."""
    mock_orch = AsyncMock()
    mock_orch.route.return_value = _unsafe_handoff_result()
    mock_orch_class.return_value = mock_orch
    mock_build.return_value = "Handing off."

    resp = client.post("/query", json={"query": "send me somewhere"})

    assert resp.status_code == 500
    assert resp.json()["detail"] == "Internal action routing error"


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Debug endpoints — bypass orchestration
# ---------------------------------------------------------------------------

@patch("app.api.routes_workflows.Workflow1StandardQCO")
@patch("app.api.routes_workflows.build_response", new_callable=AsyncMock)
def test_debug_workflow1_bypasses_classifier(
    mock_build: AsyncMock, mock_wf_class: MagicMock, client: TestClient
) -> None:
    """POST /debug/workflow1 calls Workflow1 directly, not the orchestration router."""
    mock_wf_instance = AsyncMock()
    mock_wf_instance.run.return_value = _not_found_result()
    mock_wf_class.return_value = mock_wf_instance
    mock_build.return_value = "No match found."

    resp = client.post("/debug/workflow1", json={"query": "steel rod certification"})
    assert resp.status_code == 200

    body = resp.json()
    assert body["workflow"] == "workflow1"
    assert body["state"] == "NOT_FOUND"
    # Verify it called the workflow directly
    mock_wf_instance.run.assert_called_once_with("steel rod certification")


@patch("app.api.routes_workflows.Workflow2Lab")
@patch("app.api.routes_workflows.build_response", new_callable=AsyncMock)
def test_debug_workflow2_bypasses_classifier(
    mock_build: AsyncMock, mock_wf_class: MagicMock, client: TestClient
) -> None:
    """POST /debug/workflow2 calls Workflow2 directly."""
    mock_wf_instance = AsyncMock()
    mock_wf_instance.run.return_value = _not_found_result()
    mock_wf_class.return_value = mock_wf_instance
    mock_build.return_value = "No labs found."

    resp = client.post("/debug/workflow2", json={"query": "find lab for cement"})
    assert resp.status_code == 200
    assert resp.json()["workflow"] == "workflow2"


@patch("app.api.routes_workflows.Workflow3Hallmarking")
@patch("app.api.routes_workflows.build_response", new_callable=AsyncMock)
def test_debug_workflow3_bypasses_classifier(
    mock_build: AsyncMock, mock_wf_class: MagicMock, client: TestClient
) -> None:
    """POST /debug/workflow3 calls Workflow3 directly."""
    mock_wf_instance = AsyncMock()
    mock_wf_instance.run.return_value = _not_found_result()
    mock_wf_class.return_value = mock_wf_instance
    mock_build.return_value = "Not in scope."

    resp = client.post("/debug/workflow3", json={"query": "what is HUID"})
    assert resp.status_code == 200
    assert resp.json()["workflow"] == "workflow3"
