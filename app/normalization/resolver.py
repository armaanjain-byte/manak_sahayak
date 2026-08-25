from app.core.entities import ExtractedAttributes
from app.generation.llm import extract_attributes as llm_extract_attributes

async def extract_attributes(raw_query: str) -> ExtractedAttributes:
    """
    Given a raw user query string, extract structured attributes
    using the real LLMClient from app/generation/llm.py.
    """
    return await llm_extract_attributes(raw_query)
