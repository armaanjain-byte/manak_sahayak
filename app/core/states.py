from enum import Enum

class ResponseState(str, Enum):
    ANSWERED = "ANSWERED"
    CLARIFICATION = "CLARIFICATION"
    CONFLICT = "CONFLICT"
    NOT_FOUND = "NOT_FOUND"
    HANDOFF = "HANDOFF"
