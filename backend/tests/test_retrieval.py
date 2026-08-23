"""
Tests for the retrieval layer.

All tests are fully offline — no live RAGFlow or Postgres instance required.
- ragflow_client: HTTP calls are intercepted via httpx_mock (pytest-httpx) or
  a manually constructed mock response using httpx.Response.
- structured: uses in-memory SQLite via the shared db_session fixture.
- candidate_ranking: pure unit test over in-memory objects.
"""
import json
from typing import Any, Dict, Generator, List

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.core.entities import ExtractedAttributes
from app.db.models import Laboratory, QCO, Standard
from app.db.session import Base
from app.retrieval.candidate_ranking import rank_candidates
from app.retrieval.ragflow_client import RagflowChunk, RagflowClient, RagflowError
from app.retrieval.structured import fetch_laboratory, fetch_qco, fetch_standard


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(name="db_session")
def fixture_db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionClass = sessionmaker(bind=engine)
    session = SessionClass()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _make_settings() -> Settings:
    """Return a minimal Settings instance for tests (no real env required)."""
    return Settings(
        ragflow_base_url="http://ragflow-test",
        ragflow_api_key="test-key",
        ragflow_dataset_id="ds-001",
        database_url="sqlite:///:memory:",
    )


def _mock_response(payload: Dict[str, Any], status_code: int = 200) -> httpx.Response:
    """Build a fake httpx.Response from a dict payload."""
    return httpx.Response(
        status_code=status_code,
        content=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
    )


# ---------------------------------------------------------------------------
# RagflowClient tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ragflow_client_parses_mocked_response() -> None:
    payload = {
        "data": {
            "chunks": [
                {
                    "id": "chunk-1",
                    "document_keyword": "IS-1234:2021",
                    "content": "This standard covers pressure cookers.",
                    "similarity": 0.92,
                },
                {
                    "id": "chunk-2",
                    "document_keyword": "IS-5678:2019",
                    "content": "This standard covers gas stoves.",
                    "similarity": 0.75,
                },
            ]
        }
    }

    # Use a transport that always returns our payload
    transport = httpx.MockTransport(
        handler=lambda req: _mock_response(payload)
    )
    mock_client = httpx.AsyncClient(transport=transport)

    client = RagflowClient(settings=_make_settings(), http_client=mock_client)
    result = await client.search("pressure cooker", top_k=5)

    assert len(result.chunks) == 2
    assert result.chunks[0].bis_entity_id == "IS-1234:2021"
    assert result.chunks[0].title == "IS-1234:2021"
    assert result.chunks[0].snippet == "This standard covers pressure cookers."
    assert result.chunks[0].similarity == 0.92
    assert result.chunks[1].bis_entity_id == "IS-5678:2019"
    assert result.chunks[1].similarity == 0.75


@pytest.mark.asyncio
async def test_ragflow_client_raises_on_non_200() -> None:
    transport = httpx.MockTransport(
        handler=lambda req: _mock_response({"error": "internal"}, status_code=500)
    )
    mock_client = httpx.AsyncClient(transport=transport)

    client = RagflowClient(settings=_make_settings(), http_client=mock_client)

    with pytest.raises(RagflowError, match="HTTP 500"):
        await client.search("pressure cooker")


@pytest.mark.asyncio
async def test_ragflow_client_raises_on_malformed_response() -> None:
    # Response 200 but missing expected "data.chunks" key
    transport = httpx.MockTransport(
        handler=lambda req: _mock_response({"unexpected": "shape"})
    )
    mock_client = httpx.AsyncClient(transport=transport)

    client = RagflowClient(settings=_make_settings(), http_client=mock_client)

    with pytest.raises(RagflowError, match="Malformed"):
        await client.search("helmet")


# ---------------------------------------------------------------------------
# candidate_ranking tests
# ---------------------------------------------------------------------------

def _make_chunks(specs: List[tuple]) -> List[RagflowChunk]:  # type: ignore[type-arg]
    """specs: [(bis_entity_id, title, similarity)]"""
    return [
        RagflowChunk(
            bis_entity_id=s[0],
            title=s[1],
            snippet="",
            similarity=s[2],
        )
        for s in specs
    ]


def test_candidate_ranking_orders_by_score() -> None:
    chunks = _make_chunks([
        ("IS-C", "Standard C", 0.60),
        ("IS-A", "Standard A", 0.95),
        ("IS-B", "Standard B", 0.80),
    ])
    attrs = ExtractedAttributes(product_type="widget")
    ranked = rank_candidates(chunks, attrs)

    assert ranked[0].bis_entity_id == "IS-A"
    assert ranked[1].bis_entity_id == "IS-B"
    assert ranked[2].bis_entity_id == "IS-C"


def test_candidate_ranking_boosts_product_type_match() -> None:
    # Both start at 0.70; only the one containing "cooker" in title gets boosted
    chunks = _make_chunks([
        ("IS-X", "pressure cooker standard", 0.70),
        ("IS-Y", "domestic appliance standard", 0.70),
    ])
    attrs = ExtractedAttributes(product_type="cooker")
    ranked = rank_candidates(chunks, attrs)

    assert ranked[0].bis_entity_id == "IS-X"   # boosted
    assert ranked[1].bis_entity_id == "IS-Y"   # not boosted


def test_candidate_ranking_empty_list() -> None:
    attrs = ExtractedAttributes(product_type="anything")
    result = rank_candidates([], attrs)
    assert result == []


# ---------------------------------------------------------------------------
# structured.py tests
# ---------------------------------------------------------------------------

def test_fetch_standard_by_bis_entity_id(db_session: Session) -> None:
    std = Standard(
        bis_entity_id="IS-1234:2021",
        is_number="IS 1234:2021",
        title="Pressure Cooker Standard",
        scope="Covers domestic pressure cookers.",
        status="ACTIVE",
    )
    db_session.add(std)
    db_session.commit()

    result = fetch_standard(db_session, "IS-1234:2021")
    assert result is not None
    assert result.is_number == "IS 1234:2021"
    assert result.title == "Pressure Cooker Standard"


def test_fetch_standard_returns_none_on_miss(db_session: Session) -> None:
    result = fetch_standard(db_session, "IS-NONEXISTENT")
    assert result is None


def test_fetch_qco_by_bis_entity_id(db_session: Session) -> None:
    qco = QCO(
        bis_entity_id="QCO-2026-001",
        qco_identifier="QCO-1234",
        product_category="Pressure Cookers",
        ministry="Ministry of Consumer Affairs",
        mandatory=True,
    )
    db_session.add(qco)
    db_session.commit()

    result = fetch_qco(db_session, "QCO-2026-001")
    assert result is not None
    assert result.qco_identifier == "QCO-1234"
    assert result.mandatory is True


def test_fetch_qco_returns_none_on_miss(db_session: Session) -> None:
    assert fetch_qco(db_session, "QCO-NONEXISTENT") is None


def test_fetch_laboratory_by_bis_entity_id(db_session: Session) -> None:
    lab = Laboratory(
        bis_entity_id="LAB-001",
        name="Central Testing Lab",
        recognition_status="RECOGNIZED",
        scope="Mechanical testing",
        location="New Delhi",
    )
    db_session.add(lab)
    db_session.commit()

    result = fetch_laboratory(db_session, "LAB-001")
    assert result is not None
    assert result.name == "Central Testing Lab"
    assert result.recognition_status == "RECOGNIZED"


def test_fetch_laboratory_returns_none_on_miss(db_session: Session) -> None:
    assert fetch_laboratory(db_session, "LAB-NONEXISTENT") is None
