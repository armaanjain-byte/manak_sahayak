"""
Tests for the Orchestration Router.

Verifies that raw queries are correctly dispatched to the appropriate workflows
based on the LLM intent classification, and that unclassified queries fall back
safely to the official BIS handoff.

Critically checks that the router does not duplicate gate-readiness checks.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from app.db.session import Base
from app.core.states import ResponseState
from app.core.entities import DecisionObject, Evidence, ClarificationRequest
from app.generation.llm import Intent
from app.actions.destinations import BIS_MAIN_URL
from app.orchestration.router import OrchestrationRouter
from app.workflows.base import WorkflowResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(name="db_session")
def fixture_db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = Session(bind=engine)
    return session


@pytest.fixture(name="mock_ragflow_client")
def fixture_mock_ragflow_client() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# Tests — Dispatch to Workflows
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.orchestration.router.classify_intent")
@patch("app.orchestration.router.Workflow1StandardQCO")
async def test_router_dispatches_workflow_1(
    mock_wf1_class: MagicMock,
    mock_classify: AsyncMock,
    db_session: Session,
    mock_ragflow_client: MagicMock,
) -> None:
    """Intent.WORKFLOW_1 correctly instantiates and runs Workflow1StandardQCO."""
    mock_classify.return_value = Intent.WORKFLOW_1
    
    expected_result = WorkflowResult(state=ResponseState.NOT_FOUND)
    mock_wf_instance = AsyncMock()
    mock_wf_instance.run.return_value = expected_result
    mock_wf1_class.return_value = mock_wf_instance

    router = OrchestrationRouter(session=db_session, ragflow_client=mock_ragflow_client)
    result = await router.route("my toy needs certification")

    # Verify classification was called
    mock_classify.assert_called_once_with("my toy needs certification", mock_ragflow_client)
    
    # Verify workflow 1 was instantiated and run
    mock_wf1_class.assert_called_once_with(session=db_session, ragflow_client=mock_ragflow_client)
    mock_wf_instance.run.assert_called_once_with("my toy needs certification")
    
    # Verify the result is passed through unmodified
    assert result == expected_result


@pytest.mark.asyncio
@patch("app.orchestration.router.classify_intent")
@patch("app.orchestration.router.Workflow2Lab")
async def test_router_dispatches_workflow_2(
    mock_wf2_class: MagicMock,
    mock_classify: AsyncMock,
    db_session: Session,
    mock_ragflow_client: MagicMock,
) -> None:
    """Intent.WORKFLOW_2 correctly instantiates and runs Workflow2Lab."""
    mock_classify.return_value = Intent.WORKFLOW_2
    
    expected_result = WorkflowResult(
        state=ResponseState.ANSWERED, 
        decision=DecisionObject(), 
        evidence=[Evidence(source_id="test", source_type="test", content="test", authoritative=True)]
    )
    mock_wf_instance = AsyncMock()
    mock_wf_instance.run.return_value = expected_result
    mock_wf2_class.return_value = mock_wf_instance

    router = OrchestrationRouter(session=db_session, ragflow_client=mock_ragflow_client)
    result = await router.route("find me a lab for cement")

    mock_classify.assert_called_once_with("find me a lab for cement", mock_ragflow_client)
    mock_wf2_class.assert_called_once_with(session=db_session, ragflow_client=mock_ragflow_client)
    mock_wf_instance.run.assert_called_once_with("find me a lab for cement")
    
    assert result == expected_result


@pytest.mark.asyncio
@patch("app.orchestration.router.classify_intent")
@patch("app.orchestration.router.Workflow3Hallmarking")
async def test_router_dispatches_workflow_3(
    mock_wf3_class: MagicMock,
    mock_classify: AsyncMock,
    db_session: Session,
    mock_ragflow_client: MagicMock,
) -> None:
    """Intent.WORKFLOW_3 correctly instantiates and runs Workflow3Hallmarking."""
    mock_classify.return_value = Intent.WORKFLOW_3
    
    expected_result = WorkflowResult(
        state=ResponseState.ANSWERED, 
        decision=DecisionObject(), 
        evidence=[Evidence(source_id="test", source_type="test", content="test", authoritative=True)]
    )
    mock_wf_instance = AsyncMock()
    mock_wf_instance.run.return_value = expected_result
    mock_wf3_class.return_value = mock_wf_instance

    router = OrchestrationRouter(session=db_session, ragflow_client=mock_ragflow_client)
    result = await router.route("what is HUID")

    mock_classify.assert_called_once_with("what is HUID", mock_ragflow_client)
    # Workflow 3 doesn't take ragflow_client
    mock_wf3_class.assert_called_once_with(session=db_session)
    mock_wf_instance.run.assert_called_once_with("what is HUID")
    
    assert result == expected_result


# ---------------------------------------------------------------------------
# Tests — Fallback and Gate Checking
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.orchestration.router.classify_intent")
async def test_router_unclassified_fallback(
    mock_classify: AsyncMock,
    db_session: Session,
    mock_ragflow_client: MagicMock,
) -> None:
    """Intent.UNCLASSIFIED safely hands off to the main BIS site."""
    mock_classify.return_value = Intent.UNCLASSIFIED
    
    router = OrchestrationRouter(session=db_session, ragflow_client=mock_ragflow_client)
    result = await router.route("i have a generic complaint about the website")

    assert result.state == ResponseState.HANDOFF
    assert result.action is not None
    assert result.action.destination_url == BIS_MAIN_URL
    assert result.action.action_type == "general_bis_handoff"
    assert result.decision is None


@pytest.mark.asyncio
@patch("app.orchestration.router.classify_intent")
@patch("app.orchestration.router.Workflow1StandardQCO")
@patch("app.gates.registry.is_ready")
async def test_router_does_not_check_gates(
    mock_is_ready: MagicMock,
    mock_wf1_class: MagicMock,
    mock_classify: AsyncMock,
    db_session: Session,
    mock_ragflow_client: MagicMock,
) -> None:
    """
    Router trusts workflows to check their own gates.
    The router itself must never call is_ready() to block dispatch.
    """
    mock_classify.return_value = Intent.WORKFLOW_1
    
    mock_wf_instance = AsyncMock()
    mock_wf_instance.run.return_value = WorkflowResult(
        state=ResponseState.CLARIFICATION, 
        clarification=ClarificationRequest(question="test")
    )
    mock_wf1_class.return_value = mock_wf_instance

    router = OrchestrationRouter(session=db_session, ragflow_client=mock_ragflow_client)
    
    # Run the router
    await router.route("test query")

    # Assert that is_ready was NEVER called during the router's execution
    mock_is_ready.assert_not_called()
    # But the workflow WAS still called
    mock_wf_instance.run.assert_called_once()


@pytest.mark.asyncio
async def test_router_empty_query_fallback(
    db_session: Session,
    mock_ragflow_client: MagicMock,
) -> None:
    """Empty query skips classification and falls back to generic HANDOFF."""
    router = OrchestrationRouter(session=db_session, ragflow_client=mock_ragflow_client)
    
    # We shouldn't even call the classifier
    with patch("app.orchestration.router.classify_intent") as mock_classify:
        result = await router.route("   ")
        mock_classify.assert_not_called()

    assert result.state == ResponseState.HANDOFF
    assert result.action is not None
    assert result.action.destination_url == BIS_MAIN_URL
