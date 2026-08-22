from pydantic import BaseModel
from typing import Dict, Any, Optional

class GateStatus(BaseModel):
    workflow_name: str
    is_passed: bool
    current_metrics: Dict[str, Any]

def is_ready(workflow_name: str, metrics: Optional[Dict[str, Any]] = None) -> bool:
    """Stub for checking if a workflow is ready"""
    return False
