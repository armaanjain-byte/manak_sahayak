"""
Tests for Workflow 1 (Product -> Standard -> QCO).

All tests are fully offline and use in-memory SQLite and mocked retrieval.
"""
from datetime import date
from typing import Generator, List, Optional
from unittest.mock import AsyncMock, patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.states import ResponseState
from app.db.session import Base
from app.db.models import (
    CanonicalConcept,
    Standard,
    ConceptStandardMapping,
    QCO,
    QCOStandardMapping,
)
from app.retrieval.ragflow_client import RagflowChunk, RagflowSearchResult
from app.gates.registry import registry as global_registry
from app.workflows.workflow1_standard_qco import Workflow1StandardQCO


# ---------------------------------------------------------------------------
# Mock RagflowClient
# ---------------------------------------------------------------------------
class MockRagflowClient:
    def __init__(self, chunks: List[RagflowChunk]) -> None:
        self.chunks = chunks

    async def search(self, query: str, top_k: int = 10) -> RagflowSearchResult:
        return RagflowSearchResult(chunks=self.chunks)


# ---------------------------------------------------------------------------
# Database Fixture
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


# ---------------------------------------------------------------------------
# Helper functions for seeding
# ---------------------------------------------------------------------------
def _seed_concept(session: Session, name: str, domain: str) -> CanonicalConcept:
    concept = CanonicalConcept(
        bis_entity_id=f"CON-{name.upper()}",
        name=name,
        domain=domain,
    )
    session.add(concept)
    session.commit()
    return concept


def _seed_standard(session: Session, is_number: str, title: str) -> Standard:
    std = Standard(
        bis_entity_id=is_number.replace(" ", "-"),
        is_number=is_number,
        title=title,
        scope=f"{title} - Scope of {is_number}",
        status="ACTIVE",
    )
    session.add(std)
    session.commit()
    return std


def _seed_mapping(session: Session, concept: CanonicalConcept, standard: Standard) -> None:
    mapping = ConceptStandardMapping(
        concept_id=concept.id,
        standard_id=standard.id,
        validated=True,
    )
    session.add(mapping)
    session.commit()


def _seed_qco(
    session: Session,
    qco_id: str,
    standard: Standard,
    mandatory: bool = True,
    effective_from: Optional[date] = None,
) -> QCO:
    qco = QCO(
        bis_entity_id=f"QCO-{qco_id}",
        qco_identifier=qco_id,
        product_category="Test Category",
        ministry="Ministry of Consumer Affairs",
        mandatory=mandatory,
        effective_from=effective_from,
    )
    session.add(qco)
    session.commit()

    mapping = QCOStandardMapping(
        qco_bis_entity_id=qco.bis_entity_id,
        standard_bis_entity_id=standard.bis_entity_id,
    )
    session.add(mapping)
    session.commit()
    return qco


def _set_gate_ready(ready: bool) -> None:
    if ready:
        global_registry.update_metrics(
            "workflow_1",
            {
                "canonical_concepts": 30,
                "aliases": 80,
                "validated_standard_mappings": 25,
                "validated_qco_mappings": 15,
            },
        )
    else:
        global_registry.update_metrics("workflow_1", {})


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workflow1_no_concept_match(db_session: Session) -> None:
    # Seed nothing, gate ready or not
    _set_gate_ready(True)
    
    mock_client = MockRagflowClient(chunks=[])
    workflow = Workflow1StandardQCO(session=db_session, ragflow_client=mock_client)
    
    result = await workflow.run("unknown query")
    assert result.state == ResponseState.NOT_FOUND
    assert result.decision is None


@pytest.mark.asyncio
async def test_workflow1_gate_not_ready_single_candidate_clarification(db_session: Session) -> None:
    """
    When the gate is NOT ready and only one candidate standard is found,
    the workflow must return CLARIFICATION — not HANDOFF or ANSWERED.
    Naming a specific standard to the user (even in a HANDOFF URL) is
    tantamount to resolving it, which requires A1 to be passed.
    """
    _set_gate_ready(False)

    # Seed 1 concept and 1 standard mapped
    concept = _seed_concept(db_session, "cooker", "Appliances")
    std = _seed_standard(db_session, "IS 2345:2021", "Pressure Cooker Standard")
    _seed_mapping(db_session, concept, std)

    chunks = [
        RagflowChunk(
            bis_entity_id=std.bis_entity_id,
            title=std.title,
            snippet="Test snippet",
            similarity=0.95,
        )
    ]
    mock_client = MockRagflowClient(chunks=chunks)
    workflow = Workflow1StandardQCO(session=db_session, ragflow_client=mock_client)

    result = await workflow.run("cooker")

    # Single-candidate fallback must be CLARIFICATION, not HANDOFF.
    assert result.state == ResponseState.CLARIFICATION
    assert result.clarification is not None
    assert result.clarification.options is not None
    assert len(result.clarification.options) == 1
    assert "IS 2345:2021" in result.clarification.options[0]
    # Must never carry a decision or a specific action URL naming the standard
    assert result.decision is None
    assert result.action is None


@pytest.mark.asyncio
async def test_workflow1_gate_not_ready_multiple_candidates_clarification(db_session: Session) -> None:
    """
    When the gate is NOT ready and multiple candidates exist, all are
    presented as unconfirmed options in a CLARIFICATION state.
    """
    _set_gate_ready(False)

    # Seed 1 concept and 2 standards mapped
    concept = _seed_concept(db_session, "helmet", "Safety")
    std1 = _seed_standard(db_session, "IS 4151:2015", "Helmet Standard 1")
    std2 = _seed_standard(db_session, "IS 9999:2020", "Helmet Standard 2")
    _seed_mapping(db_session, concept, std1)
    _seed_mapping(db_session, concept, std2)

    chunks = [
        RagflowChunk(
            bis_entity_id=std1.bis_entity_id,
            title=std1.title,
            snippet="",
            similarity=0.90,
        ),
        RagflowChunk(
            bis_entity_id=std2.bis_entity_id,
            title=std2.title,
            snippet="",
            similarity=0.88,
        ),
    ]
    mock_client = MockRagflowClient(chunks=chunks)
    workflow = Workflow1StandardQCO(session=db_session, ragflow_client=mock_client)

    result = await workflow.run("helmet")

    # Bounded fallback: should return CLARIFICATION
    assert result.state == ResponseState.CLARIFICATION
    assert result.clarification is not None
    assert result.clarification.options is not None
    assert len(result.clarification.options) == 2
    assert "IS 4151:2015" in result.clarification.options[0]
    assert "IS 9999:2020" in result.clarification.options[1]


@pytest.mark.asyncio
async def test_workflow1_clean_single_match(db_session: Session) -> None:
    # Gate is ready
    _set_gate_ready(True)

    concept = _seed_concept(db_session, "toy", "Toys")
    std = _seed_standard(db_session, "IS 9873:2017", "Safety of Toys")
    _seed_mapping(db_session, concept, std)
    _seed_qco(db_session, "QCO-TOYS-001", std, mandatory=True, effective_from=date(2026, 9, 1))

    chunks = [
        RagflowChunk(
            bis_entity_id=std.bis_entity_id,
            title=std.title,
            snippet="Toys standard",
            similarity=0.98,
        )
    ]
    mock_client = MockRagflowClient(chunks=chunks)
    workflow = Workflow1StandardQCO(session=db_session, ragflow_client=mock_client)

    result = await workflow.run("toy")

    # Should return ANSWERED with correct decision and evidence
    assert result.state == ResponseState.ANSWERED
    assert result.decision is not None
    assert result.decision.standard == std.is_number
    assert result.decision.mandatory is True
    assert result.decision.basis == "QCO-TOYS-001"
    assert result.decision.effective_from == "2026-09-01"
    assert result.decision.confidence.value == "HIGH"
    
    assert len(result.evidence) == 2
    assert result.evidence[0].source_type == "standard"
    assert result.evidence[0].authoritative is True
    assert result.evidence[1].source_type == "qco"
    assert result.evidence[1].authoritative is True


@pytest.mark.asyncio
@patch("app.workflows.workflow1_standard_qco.extract_attributes", new_callable=AsyncMock)
async def test_workflow1_normalizes_extracted_product_type(
    mock_extract: AsyncMock,
    db_session: Session,
) -> None:
    _set_gate_ready(True)
    mock_extract.return_value.product_type = "pressure cooker"

    concept = _seed_concept(db_session, "pressure cooker", "Kitchenware")
    std = _seed_standard(db_session, "IS 2347:2017", "Domestic Pressure Cookers")
    _seed_mapping(db_session, concept, std)

    chunks = [
        RagflowChunk(
            bis_entity_id=std.bis_entity_id,
            title=std.title,
            snippet="",
            similarity=0.99,
        )
    ]
    mock_client = MockRagflowClient(chunks=chunks)
    workflow = Workflow1StandardQCO(session=db_session, ragflow_client=mock_client)

    result = await workflow.run("Do I need BIS certification for my pressure cooker?")

    assert result.state == ResponseState.ANSWERED
    assert result.decision is not None
    assert result.decision.standard == "IS 2347:2017"


@pytest.mark.asyncio
async def test_workflow1_multiple_candidates_clarification(db_session: Session) -> None:
    # Gate is ready
    _set_gate_ready(True)

    concept = _seed_concept(db_session, "cement", "Construction")
    std1 = _seed_standard(db_session, "IS 269:2015", "OPC Cement")
    std2 = _seed_standard(db_session, "IS 455:2015", "PSC Cement")
    _seed_mapping(db_session, concept, std1)
    _seed_mapping(db_session, concept, std2)

    chunks = [
        RagflowChunk(
            bis_entity_id=std1.bis_entity_id,
            title=std1.title,
            snippet="",
            similarity=0.92,
        ),
        RagflowChunk(
            bis_entity_id=std2.bis_entity_id,
            title=std2.title,
            snippet="",
            similarity=0.91,
        ),
    ]
    mock_client = MockRagflowClient(chunks=chunks)
    workflow = Workflow1StandardQCO(session=db_session, ragflow_client=mock_client)

    result = await workflow.run("cement")

    # Should return CLARIFICATION
    assert result.state == ResponseState.CLARIFICATION
    assert result.clarification is not None
    assert result.clarification.options is not None
    assert len(result.clarification.options) == 2


@pytest.mark.asyncio
async def test_workflow1_conflicting_qco_evidence(db_session: Session) -> None:
    # Gate is ready
    _set_gate_ready(True)

    concept = _seed_concept(db_session, "cable", "Electrical")
    std = _seed_standard(db_session, "IS 694:2010", "PVC Cables")
    _seed_mapping(db_session, concept, std)

    # Seed two conflicting QCOs for the same standard
    _seed_qco(db_session, "QCO-CABLE-001", std, mandatory=True)
    _seed_qco(db_session, "QCO-CABLE-002", std, mandatory=False)

    chunks = [
        RagflowChunk(
            bis_entity_id=std.bis_entity_id,
            title=std.title,
            snippet="",
            similarity=0.95,
        )
    ]
    mock_client = MockRagflowClient(chunks=chunks)
    workflow = Workflow1StandardQCO(session=db_session, ragflow_client=mock_client)

    result = await workflow.run("cable")

    # Should return CONFLICT
    assert result.state == ResponseState.CONFLICT
    assert result.decision is None
    assert len(result.evidence) == 2
    assert result.evidence[0].source_type == "qco"
    assert result.evidence[1].source_type == "qco"
