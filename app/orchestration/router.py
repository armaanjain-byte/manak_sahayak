"""
Orchestration Router.

Responsible for matching raw user queries to the correct underlying workflow
(or falling back to a generic BIS handoff for unsupported queries).

The router relies on the LLM to classify intent, but it NEVER bypasses the
workflows' own internal gate-readiness checks. Dispatching to an unready
workflow is the correct path — the workflow itself knows how to fall back safely.
"""
from typing import Any
from sqlalchemy.orm import Session

from app.actions.destinations import BIS_MAIN_URL
from app.core.entities import Action
from app.core.states import ResponseState
from app.generation.llm import Intent, classify_intent
from app.workflows.base import WorkflowResult
from app.workflows.workflow1_standard_qco import Workflow1StandardQCO
from app.workflows.workflow2_lab import Workflow2Lab
from app.workflows.workflow3_hallmarking import Workflow3Hallmarking


class OrchestrationRouter:
    """
    Top-level router orchestrating the reasoning layer.
    """
    def __init__(self, session: Session, ragflow_client: Any) -> None:
        self.session = session
        self.ragflow_client = ragflow_client

    async def route(self, query: str) -> WorkflowResult:
        """
        Classifies the query intent and dispatches it to the correct workflow.
        
        Args:
            query: The raw user query.
            
        Returns:
            The WorkflowResult directly from the target workflow, or a generic
            HANDOFF if the query is unclassified.
        """
        query = query.strip()
        if not query:
            return self._fallback()

        intent = await classify_intent(query, self.ragflow_client)

        if intent == Intent.WORKFLOW_1:
            workflow_1 = Workflow1StandardQCO(
                session=self.session, 
                ragflow_client=self.ragflow_client
            )
            return await workflow_1.run(query)
            
        if intent == Intent.WORKFLOW_2:
            workflow_2 = Workflow2Lab(
                session=self.session, 
                ragflow_client=self.ragflow_client
            )
            return await workflow_2.run(query)
            
        if intent == Intent.WORKFLOW_3:
            workflow_3 = Workflow3Hallmarking(
                session=self.session
            )
            return await workflow_3.run(query)

        # Intent.UNCLASSIFIED
        return self._fallback()

    def _fallback(self) -> WorkflowResult:
        """
        The top-level generic fallback.
        
        Per the PRD, we do not silently fall back to generic RAG or guess
        regulatory facts for unsupported domains. We hand the user off to the
        official BIS main site.
        """
        return WorkflowResult(
            state=ResponseState.HANDOFF,
            action=Action(
                action_type="general_bis_handoff",
                destination_url=BIS_MAIN_URL
            ),
            evidence=[]
        )
