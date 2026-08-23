"""
Provider-abstracted LLM client.

Wraps the Anthropic API to classify intents, extract attributes, and
generate natural language responses while strictly adhering to the facts
boundary.
"""
import json
from typing import Any
from anthropic import AsyncAnthropic
from anthropic.types import TextBlock

from app.config import get_settings
from app.core.entities import ExtractedAttributes, DecisionObject, Evidence, ClarificationRequest
from app.generation.prompts import (
    INTENT_CLASSIFICATION_PROMPT,
    ATTRIBUTE_EXTRACTION_PROMPT,
    CLARIFICATION_PROMPT,
    DECISION_EXPLANATION_PROMPT
)


# Must match the enum from previous phase for the router to work
from enum import Enum, auto
class Intent(Enum):
    WORKFLOW_1 = auto()    # Standard / QCO reasoning
    WORKFLOW_2 = auto()    # Laboratory discovery
    WORKFLOW_3 = auto()    # Hallmarking / HUID consumer guidance
    UNCLASSIFIED = auto()  # General query outside deep workflows


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        # Allow client to be instantiated without an API key for testing
        self.client = AsyncAnthropic(api_key=self.api_key) if self.api_key else None

    async def _generate(self, system: str, user: str) -> str:
        """Internal helper to call the Anthropic API."""
        if not self.client:
            raise RuntimeError("LLM API key not configured.")
            
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}]
        )
        # Filter only TextBlock items and take the first one.
        text_blocks = [b for b in response.content if isinstance(b, TextBlock)]
        if not text_blocks:
            raise RuntimeError("LLM returned no text content.")
        return text_blocks[0].text


async def classify_intent(query: str, ragflow_client: Any = None) -> Intent:
    """Classify a user query into one of the core orchestration intents."""
    client = LLMClient()
    prompt = INTENT_CLASSIFICATION_PROMPT.format(query=query)
    try:
        response_text = await client._generate(
            system="You are a classifier. Respond ONLY with the category name.",
            user=prompt
        )
        clean_text = response_text.strip().upper()
        if "WORKFLOW_1" in clean_text:
            return Intent.WORKFLOW_1
        elif "WORKFLOW_2" in clean_text:
            return Intent.WORKFLOW_2
        elif "WORKFLOW_3" in clean_text:
            return Intent.WORKFLOW_3
        else:
            return Intent.UNCLASSIFIED
    except Exception:
        # Fail safe to unclassified
        return Intent.UNCLASSIFIED


async def extract_attributes(query: str) -> ExtractedAttributes:
    """Extract structured attributes from a raw query."""
    client = LLMClient()
    prompt = ATTRIBUTE_EXTRACTION_PROMPT.format(query=query)
    try:
        response_text = await client._generate(
            system="You are an attribute extractor. Respond ONLY with valid JSON.",
            user=prompt
        )
        # Simple extraction for robustness against markdown wrapping
        json_str = response_text
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0].strip()
            
        data = json.loads(json_str)
        return ExtractedAttributes(**data)
    except Exception:
        # Fallback if extraction fails
        return ExtractedAttributes(product_type=query.strip())


async def generate_clarification(decision: DecisionObject | None, clarification: ClarificationRequest) -> str:
    """Generate a polite clarification request based on the missing information."""
    client = LLMClient()
    options_str = ", ".join(clarification.options) if clarification.options else "None provided"
    prompt = CLARIFICATION_PROMPT.format(
        question=clarification.question,
        options=options_str
    )
    return await client._generate(
        system="You are a helpful BIS assistant asking for clarification.",
        user=prompt
    )


async def explain_decision(decision: DecisionObject, evidence: list[Evidence]) -> str:
    """Explain a regulatory decision based ONLY on the provided JSON data."""
    client = LLMClient()
    decision_json = decision.model_dump_json(exclude_none=True)
    evidence_json = json.dumps([e.model_dump() for e in evidence])
    
    prompt = DECISION_EXPLANATION_PROMPT.format(
        decision_json=decision_json,
        evidence_json=evidence_json
    )
    return await client._generate(
        system="You are a strict BIS assistant. Only use the provided JSON facts.",
        user=prompt
    )
