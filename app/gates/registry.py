from pydantic import BaseModel
from typing import Dict, Any
from app.gates.status import WorkflowStatus
from app.gates.criteria import A1_TARGETS, A2_TARGETS, A3_TARGETS, GateCriteria

class GateStatus(BaseModel):
    workflow_name: str
    is_passed: bool
    current_metrics: Dict[str, Any]
    status: WorkflowStatus

# Map workflow name to its criteria
WORKFLOW_CRITERIA: Dict[str, GateCriteria] = {
    "workflow_1": A1_TARGETS,
    "workflow_2": A2_TARGETS,
    "workflow_3": A3_TARGETS,
}

class GateRegistry:
    def __init__(self) -> None:
        # TODO: Wire to real data (e.g., Postgres or JSON file) in a later phase.
        self._metrics: Dict[str, Dict[str, Any]] = {}

    def load_metrics(self, metrics: Dict[str, Dict[str, Any]]) -> None:
        """Load current metrics for all workflows."""
        self._metrics = metrics
        
    def update_metrics(self, workflow_name: str, metrics: Dict[str, Any]) -> None:
        """Update metrics for a specific workflow."""
        self._metrics[workflow_name] = metrics

    def get_metrics(self, workflow_name: str) -> Dict[str, Any]:
        """Get current metrics for a specific workflow."""
        return self._metrics.get(workflow_name, {})

    def is_ready(self, workflow_name: str) -> bool:
        """
        Check if a workflow meets or exceeds all its gate criteria.
        A gate is ready only if EVERY field meets or exceeds its target.
        """
        criteria = WORKFLOW_CRITERIA.get(workflow_name)
        if not criteria:
            return False
            
        current = self.get_metrics(workflow_name)
        if not current:
            return False
            
        # Compare field-by-field.
        for field, target_val in criteria.model_dump().items():
            current_val = current.get(field, 0)
            if current_val < target_val:
                return False
                
        return True

    def get_status(self, workflow_name: str) -> WorkflowStatus:
        """Return SPEC, PARTIAL, or BUILD based on gate state."""
        current = self.get_metrics(workflow_name)
        if not current:
            return WorkflowStatus.SPEC
            
        if self.is_ready(workflow_name):
            return WorkflowStatus.BUILD
            
        return WorkflowStatus.PARTIAL
        
    def get_gate_status(self, workflow_name: str) -> GateStatus:
        """Return the full GateStatus object."""
        return GateStatus(
            workflow_name=workflow_name,
            is_passed=self.is_ready(workflow_name),
            current_metrics=self.get_metrics(workflow_name),
            status=self.get_status(workflow_name)
        )

# Global instance for easy importing
registry = GateRegistry()

def is_ready(workflow_name: str) -> bool:
    return registry.is_ready(workflow_name)

def get_status(workflow_name: str) -> WorkflowStatus:
    return registry.get_status(workflow_name)
