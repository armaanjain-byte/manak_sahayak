import pytest
from app.workflows.base import Workflow, WorkflowResult
from app.core.states import ResponseState
from app.core.entities import DecisionObject, Evidence, ClarificationRequest

class DummyWorkflow(Workflow):
    async def run(self, context):
        pass

def test_workflow_result_answered_without_decision_raises():
    with pytest.raises(ValueError, match="ANSWERED requires a decision"):
        WorkflowResult(
            state=ResponseState.ANSWERED,
            evidence=[Evidence(source_id="1", source_type="qco", content="test", authoritative=True)]
        )

def test_workflow_result_answered_without_authoritative_evidence_raises():
    with pytest.raises(ValueError, match="ANSWERED requires at least one authoritative evidence item"):
        WorkflowResult(
            state=ResponseState.ANSWERED,
            decision=DecisionObject(),
            evidence=[Evidence(source_id="1", source_type="qco", content="test", authoritative=False)]
        )

def test_workflow_result_clarification_with_decision_raises():
    with pytest.raises(ValueError, match="CLARIFICATION must not have a decision"):
        WorkflowResult(
            state=ResponseState.CLARIFICATION,
            clarification=ClarificationRequest(question="?"),
            decision=DecisionObject()
        )

def test_workflow_result_clarification_without_clarification_raises():
    with pytest.raises(ValueError, match="CLARIFICATION requires a clarification object"):
        WorkflowResult(
            state=ResponseState.CLARIFICATION
        )

def test_workflow_result_conflict_without_evidence_raises():
    with pytest.raises(ValueError, match="CONFLICT requires conflicting evidence items"):
        WorkflowResult(
            state=ResponseState.CONFLICT,
            evidence=[Evidence(source_id="1", source_type="qco", content="test")]
        )

def test_workflow_result_not_found_with_decision_raises():
    with pytest.raises(ValueError, match="NOT_FOUND must not have a decision"):
        WorkflowResult(
            state=ResponseState.NOT_FOUND,
            decision=DecisionObject()
        )

def test_workflow_result_handoff_without_action_raises():
    with pytest.raises(ValueError, match="HANDOFF requires an action with a destination URL"):
        WorkflowResult(
            state=ResponseState.HANDOFF
        )
