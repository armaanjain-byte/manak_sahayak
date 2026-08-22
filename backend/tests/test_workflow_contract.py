import pytest
from app.workflows.base import Workflow, WorkflowResult
from app.core.states import ResponseState
from app.core.entities import DecisionObject, Evidence, ClarificationRequest

class DummyWorkflow(Workflow):
    def run(self, context):
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
