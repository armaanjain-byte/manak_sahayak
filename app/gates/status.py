from enum import Enum

class WorkflowStatus(str, Enum):
    SPEC = "SPEC"
    PARTIAL = "PARTIAL"
    BUILD = "BUILD"
