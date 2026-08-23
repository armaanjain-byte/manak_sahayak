"""
Response Builder.

Takes a WorkflowResult and produces the final natural language text
for the user, utilizing the LLM only for explaining pre-established
facts or generating clarification questions.
"""
from app.core.states import ResponseState
from app.workflows.base import WorkflowResult
from app.generation.llm import explain_decision, generate_clarification


async def build_response(result: WorkflowResult) -> str:
    """
    Produce the final user-facing string from a WorkflowResult.
    
    Args:
        result: The result from a workflow.
        
    Returns:
        A natural language string for the user.
    """
    if result.state == ResponseState.ANSWERED:
        if not result.decision:
            return "The system encountered an error: ANSWERED state missing decision."
        return await explain_decision(result.decision, result.evidence)
        
    elif result.state == ResponseState.CLARIFICATION:
        if not result.clarification:
            return "I need more information to answer your query, but no specific question was provided."
        return await generate_clarification(result.decision, result.clarification)
        
    elif result.state == ResponseState.NOT_FOUND:
        return "I could not find a relevant standard or regulatory requirement for your query in the current BIS records."
        
    elif result.state == ResponseState.CONFLICT:
        return "I found conflicting evidence regarding your query and cannot provide a definitive answer."
        
    elif result.state == ResponseState.HANDOFF:
        return "I am handing you off to the official BIS service for further action."
        
    return "An unknown error occurred."
