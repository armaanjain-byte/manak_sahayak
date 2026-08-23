from typing import Optional, List
from pydantic import BaseModel
from enum import Enum

class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"

class DecisionObject(BaseModel):
    standard: Optional[str] = None
    mandatory: Optional[bool] = None
    basis: Optional[str] = None
    effective_from: Optional[str] = None
    pathway: Optional[str] = None
    confidence: Confidence = Confidence.INSUFFICIENT

class Evidence(BaseModel):
    source_id: str
    source_type: str
    content: str
    authoritative: bool = False

class ClarificationRequest(BaseModel):
    question: str
    options: Optional[List[str]] = None

class Action(BaseModel):
    action_type: str
    destination_url: str
