"""
Tests for the Generation layer (llm.py, prompts.py, response_builder.py).

All LLM API calls are mocked — no real network calls in tests.
Key assertions:
- response_builder produces the correct output shape for each ResponseState.
- The prompt sent for ANSWERED explanations explicitly includes the
  DecisionObject's actual fields (standard, mandatory, effective_from).
- The LLM client is fully mockable via constructor injection.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.states import ResponseState
from app.core.entities import (
    DecisionObject,
    Evidence,
    ClarificationRequest,
    Confidence,
)
from app.generation.llm import LLMClient, Intent, classify_intent, explain_decision, extract_attributes
from app.generation.prompts import (
    ATTRIBUTE_EXTRACTION_PROMPT,
)
from app.generation.response_builder import build_response
from app.workflows.base import WorkflowResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_decision() -> DecisionObject:
    return DecisionObject(
        standard="IS 1234",
        mandatory=True,
        basis="QCO/2023/IS1234",
        effective_from="2023-01-01",
        confidence=Confidence.HIGH,
    )


@pytest.fixture
def sample_evidence() -> list[Evidence]:
    return [
        Evidence(
            source_id="ev-1",
            source_type="qco_gazette",
            content="IS 1234 is mandatory per QCO/2023/IS1234 effective 2023-01-01",
            authoritative=True,
        )
    ]


# ---------------------------------------------------------------------------
# LLMClient — mockability
# ---------------------------------------------------------------------------

def test_llm_client_can_be_instantiated_without_key() -> None:
    """LLMClient can be created without an API key (for test environments)."""
    client = LLMClient(api_key="")
    assert client.client is None  # No key → no real API client


@pytest.mark.asyncio
async def test_llm_client_generate_raises_without_key() -> None:
    """Calling _generate without a configured key raises RuntimeError."""
    client = LLMClient(api_key="")
    with pytest.raises(RuntimeError, match="API key not configured"):
        await client._generate(system="sys", user="user")


@pytest.mark.asyncio
async def test_llm_client_generate_calls_anthropic() -> None:
    """_generate calls the Anthropic client with correct model and messages."""
    from anthropic.types import TextBlock as AnthropicTextBlock

    client = LLMClient(api_key="test-key", model="claude-3-5-sonnet-20241022")

    mock_response = MagicMock()
    mock_response.content = [AnthropicTextBlock(type="text", text="WORKFLOW_1")]

    client.client = AsyncMock()
    client.client.messages.create = AsyncMock(return_value=mock_response)

    result = await client._generate(system="You are a classifier.", user="test query")

    assert result == "WORKFLOW_1"
    client.client.messages.create.assert_called_once_with(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        system="You are a classifier.",
        messages=[{"role": "user", "content": "test query"}]
    )


# ---------------------------------------------------------------------------
# classify_intent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.generation.llm.LLMClient")
async def test_classify_intent_workflow1(mock_client_class: MagicMock) -> None:
    """classify_intent correctly maps 'WORKFLOW_1' response to Intent.WORKFLOW_1."""
    mock_instance = MagicMock()
    mock_instance._generate = AsyncMock(return_value="WORKFLOW_1")
    mock_client_class.return_value = mock_instance

    result = await classify_intent("is cement mandatory?")
    assert result == Intent.WORKFLOW_1


@pytest.mark.asyncio
@patch("app.generation.llm.LLMClient")
async def test_classify_intent_unclassified_on_error(mock_client_class: MagicMock) -> None:
    """classify_intent falls back to UNCLASSIFIED when the LLM raises."""
    mock_instance = MagicMock()
    mock_instance._generate = AsyncMock(side_effect=RuntimeError("API key not configured"))
    mock_client_class.return_value = mock_instance

    result = await classify_intent("some query")
    assert result == Intent.UNCLASSIFIED


# ---------------------------------------------------------------------------
# Decision Explanation Prompt — content assertions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_explain_decision_prompt_contains_decision_fields(
    sample_decision: DecisionObject,
    sample_evidence: list[Evidence],
) -> None:
    """
    The prompt sent to the LLM for an ANSWERED explanation must explicitly
    include the decision's standard, mandatory flag, and effective_from date.
    This ensures the LLM is grounded in actual facts.
    """
    captured_prompt: list[str] = []

    async def capture_generate(system: str, user: str) -> str:
        captured_prompt.append(user)
        return "Explanation generated."

    client = LLMClient(api_key="test-key")
    client._generate = capture_generate  # type: ignore[method-assign]

    with patch("app.generation.llm.LLMClient", return_value=client):
        await explain_decision(sample_decision, sample_evidence)

    assert len(captured_prompt) == 1
    prompt_sent = captured_prompt[0]

    # The actual decision fields must appear in the prompt context
    assert "IS 1234" in prompt_sent, "Decision standard must be in prompt"
    assert "true" in prompt_sent.lower() or '"mandatory": true' in prompt_sent, (
        "Mandatory status must be in prompt"
    )
    assert "2023-01-01" in prompt_sent, "Effective date must be in prompt"


# ---------------------------------------------------------------------------
# Attribute extraction prompt — key fields
# ---------------------------------------------------------------------------

def test_attribute_extraction_prompt_contains_query() -> None:
    """The extraction prompt template includes the raw user query."""
    query = "I manufacture ceramic insulators for high-voltage transmission"
    prompt = ATTRIBUTE_EXTRACTION_PROMPT.format(query=query)
    assert query in prompt


@pytest.mark.asyncio
@patch("app.generation.llm.LLMClient")
async def test_extract_attributes_parses_json(mock_client_class: MagicMock) -> None:
    """extract_attributes correctly parses a valid JSON response."""
    mock_instance = MagicMock()
    payload = {
        "product_type": "ceramic insulators",
        "material": "ceramic",
        "intended_use": "high-voltage transmission",
        "is_imported": False,
        "technical_attributes": ["high-voltage"]
    }
    mock_instance._generate = AsyncMock(return_value=json.dumps(payload))
    mock_client_class.return_value = mock_instance

    attrs = await extract_attributes("I manufacture ceramic insulators for high-voltage transmission")
    assert attrs.product_type == "ceramic insulators"
    assert attrs.material == "ceramic"
    assert attrs.is_imported is False


# ---------------------------------------------------------------------------
# response_builder — shape per state
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.generation.response_builder.explain_decision", new_callable=AsyncMock)
async def test_response_builder_answered_calls_explain(
    mock_explain: AsyncMock,
    sample_decision: DecisionObject,
    sample_evidence: list[Evidence],
) -> None:
    """ANSWERED state delegates explanation to explain_decision."""
    mock_explain.return_value = "This standard is mandatory."

    result_obj = WorkflowResult(
        state=ResponseState.ANSWERED,
        decision=sample_decision,
        evidence=sample_evidence,
    )
    text = await build_response(result_obj)

    mock_explain.assert_called_once_with(sample_decision, sample_evidence)
    assert text == "This standard is mandatory."


@pytest.mark.asyncio
@patch("app.generation.response_builder.generate_clarification", new_callable=AsyncMock)
async def test_response_builder_clarification_calls_generate(
    mock_gen: AsyncMock,
) -> None:
    """CLARIFICATION state delegates to generate_clarification."""
    mock_gen.return_value = "Could you clarify your product type?"

    result_obj = WorkflowResult(
        state=ResponseState.CLARIFICATION,
        clarification=ClarificationRequest(question="What type of product?"),
    )
    text = await build_response(result_obj)

    mock_gen.assert_called_once()
    assert text == "Could you clarify your product type?"


@pytest.mark.asyncio
async def test_response_builder_not_found() -> None:
    """NOT_FOUND returns a descriptive static message."""
    result_obj = WorkflowResult(state=ResponseState.NOT_FOUND)
    text = await build_response(result_obj)
    assert "not find" in text.lower() or "could not" in text.lower()


@pytest.mark.asyncio
async def test_response_builder_conflict() -> None:
    """CONFLICT returns a message about conflicting evidence."""
    result_obj = WorkflowResult(
        state=ResponseState.CONFLICT,
        evidence=[
            Evidence(source_id="a", source_type="t", content="conflict A", authoritative=True),
            Evidence(source_id="b", source_type="t", content="conflict B", authoritative=True),
        ]
    )
    text = await build_response(result_obj)
    assert "conflict" in text.lower()


@pytest.mark.asyncio
async def test_response_builder_handoff() -> None:
    """HANDOFF returns a handoff message."""
    from app.core.entities import Action
    from app.actions.destinations import BIS_CARE_APP_URL

    result_obj = WorkflowResult(
        state=ResponseState.HANDOFF,
        action=Action(action_type="huid_verification", destination_url=BIS_CARE_APP_URL)
    )
    text = await build_response(result_obj)
    assert "official" in text.lower() or "visit" in text.lower()
