from abc import ABC, abstractmethod
from typing import Optional, List, Any
from pydantic import BaseModel, model_validator
from app.core.states import ResponseState
from app.core.entities import DecisionObject, Evidence, ClarificationRequest, Action

class WorkflowResult(BaseModel):
    state: ResponseState
    decision: Optional[DecisionObject] = None
    evidence: List[Evidence] = []
    clarification: Optional[ClarificationRequest] = None
    action: Optional[Action] = None
    query: Optional[str] = None

    @model_validator(mode="after")
    def check_invariants(self) -> "WorkflowResult":
        if self.state == ResponseState.ANSWERED:
            if not self.decision:
                raise ValueError("ANSWERED requires a decision.")
            if not any(e.authoritative for e in self.evidence):
                raise ValueError("ANSWERED requires at least one authoritative evidence item.")
        
        if self.state == ResponseState.CLARIFICATION:
            if not self.clarification:
                raise ValueError("CLARIFICATION requires a clarification object.")
            if self.decision:
                raise ValueError("CLARIFICATION must not have a decision.")
                
        if self.state == ResponseState.CONFLICT:
            if len(self.evidence) < 2:
                raise ValueError("CONFLICT requires conflicting evidence items.")
                
        if self.state == ResponseState.NOT_FOUND:
            if self.decision:
                raise ValueError("NOT_FOUND must not have a decision.")
                
        if self.state == ResponseState.HANDOFF:
            if not self.action or not self.action.destination_url:
                raise ValueError("HANDOFF requires an action with a destination URL.")
                
        return self

class Workflow(ABC):
    @abstractmethod
    async def run(self, context: Any) -> WorkflowResult:
        pass
