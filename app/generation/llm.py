"""
LLM interfaces and call contracts.
(Actual implementation is Phase 10)
"""
from enum import Enum, auto
from typing import Any

class Intent(Enum):
    WORKFLOW_1 = auto()    # Standard / QCO reasoning
    WORKFLOW_2 = auto()    # Laboratory discovery
    WORKFLOW_3 = auto()    # Hallmarking / HUID consumer guidance
    UNCLASSIFIED = auto()  # General query outside deep workflows


async def classify_intent(query: str, ragflow_client: Any) -> Intent:
    """
    Classify a user query into one of the core orchestration intents.
    
    This is an allowed LLM boundary usage — it directs traffic but does not
    determine regulatory facts or simulate transactional systems.
    
    Args:
        query: The raw user input.
        ragflow_client: The client for any necessary context retrieval before classification.
        
    Returns:
        An Intent enum representing the matched workflow.
        
    Raises:
        NotImplementedError: Until Phase 10 implementation.
    """
    raise NotImplementedError("LLM integration is Phase 10")
