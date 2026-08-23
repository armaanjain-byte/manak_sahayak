from app.core.entities import ExtractedAttributes

def extract_attributes(raw_query: str) -> ExtractedAttributes:
    """
    Given a raw user query string, extract structured attributes.
    
    TODO: Implement this as an LLM-based extraction function using 
    app/generation/llm.py's interface. This currently returns a mock
    ExtractedAttributes object to define the contract.
    
    LLM CALL SITE FLAG:
    Needs real implementation in app/generation/llm.py before this is functional end-to-end.
    """
    # Mock return for this phase
    return ExtractedAttributes(
        product_type=raw_query.strip(),
        material=None,
        intended_use=None,
        is_imported=None,
        technical_attributes=[]
    )
