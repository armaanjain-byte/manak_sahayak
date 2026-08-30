"""
Tests for Workflow 2 (Standard -> Laboratory).
"""
import pytest
from datetime import date, timedelta
from typing import Generator, Any
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.states import ResponseState
from app.db.models import CanonicalConcept, ConceptStandardMapping, Standard, Laboratory
from app.db.session import Base
from app.gates.registry import registry as global_registry
from app.retrieval.ragflow_client import RagflowChunk
from app.workflows.workflow2_lab import Workflow2Lab


# ---------------------------------------------------------------------------
# Mocks & Fixtures
# ---------------------------------------------------------------------------

class MockRagflowClient:
    def __init__(self, chunks: list[RagflowChunk]) -> None:
        self.chunks = chunks

    async def search(self, query: str, top_k: int = 5) -> Any:
        class Result:
            chunks = self.chunks
        return Result()


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


def _seed_concept(session: Session, name: str, domain: str = "test") -> CanonicalConcept:
    c = CanonicalConcept(
        bis_entity_id=f"CONCEPT-{name.upper()}",
        name=name,
        domain=domain,
    )
    session.add(c)
    session.commit()
    return c


def _seed_standard(session: Session, is_number: str, title: str) -> Standard:
    s = Standard(
        bis_entity_id=f"STD-{is_number.replace(' ', '')}",
        is_number=is_number,
        title=title,
        scope="Testing scope",
        status="ACTIVE",
    )
    session.add(s)
    session.commit()
    return s


def _seed_mapping(session: Session, concept: CanonicalConcept, standard: Standard) -> None:
    m = ConceptStandardMapping(
        concept_id=concept.id,
        standard_id=standard.id,
        validated=True,
    )
    session.add(m)
    session.commit()


def _set_gate_ready(is_ready: bool) -> None:
    if is_ready:
        global_registry.update_metrics(
            "workflow_2",
            {
                "standards_with_validated_scope_mappings": 20,
                "eligible_standard_lab_relationships": 25,
                "labs_minimum": 8,
                "demo_recommended_labs_checked_percent": 100,
                "successful_e2e_lab_queries": 10,
            },
        )
    else:
        global_registry.update_metrics("workflow_2", {})


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workflow2_gate_not_ready_clarification(db_session: Session) -> None:
    _set_gate_ready(False)

    concept = _seed_concept(db_session, "helmet", "Safety")
    std = _seed_standard(db_session, "IS 4151:2015", "Helmet Standard 1")
    _seed_mapping(db_session, concept, std)

    chunks = [
        RagflowChunk(
            bis_entity_id=std.bis_entity_id,
            title=std.title,
            snippet="",
            similarity=0.90,
        )
    ]
    mock_client = MockRagflowClient(chunks=chunks)
    workflow = Workflow2Lab(session=db_session, ragflow_client=mock_client)  # type: ignore[arg-type]

    result = await workflow.run("helmet")

    # Gate unready -> must return CLARIFICATION, not a confident recommendation
    assert result.state == ResponseState.CLARIFICATION
    assert result.clarification is not None
    assert result.clarification.options is not None
    assert "IS 4151:2015" in result.clarification.options[0]


@pytest.mark.asyncio
async def test_workflow2_expired_lab_excluded(db_session: Session) -> None:
    _set_gate_ready(True)

    concept = _seed_concept(db_session, "water", "Food")
    std = _seed_standard(db_session, "IS 10500:2012", "Drinking Water")
    _seed_mapping(db_session, concept, std)

    # Valid lab
    lab1 = Laboratory(
        bis_entity_id="LAB-001",
        name="Valid Lab",
        recognition_status="RECOGNIZED",
        scope="Testing as per IS 10500:2012",
        validity=date.today() + timedelta(days=30),
        location="Delhi",
    )
    # Expired lab
    lab2 = Laboratory(
        bis_entity_id="LAB-002",
        name="Expired Lab",
        recognition_status="RECOGNIZED",
        scope="Testing as per IS 10500:2012",
        validity=date.today() - timedelta(days=5),
        location="Mumbai",
    )
    # Unrecognized lab
    lab3 = Laboratory(
        bis_entity_id="LAB-003",
        name="Unrecognized Lab",
        recognition_status="DE-RECOGNIZED",
        scope="Testing as per IS 10500:2012",
        validity=date.today() + timedelta(days=30),
        location="Chennai",
    )
    std.laboratories.extend([lab1, lab2, lab3])
    db_session.add_all([lab1, lab2, lab3])
    db_session.commit()

    chunks = [
        RagflowChunk(
            bis_entity_id=std.bis_entity_id,
            title=std.title,
            snippet="",
            similarity=0.95,
        )
    ]
    mock_client = MockRagflowClient(chunks=chunks)
    workflow = Workflow2Lab(session=db_session, ragflow_client=mock_client)  # type: ignore[arg-type]

    result = await workflow.run("water")

    assert result.state == ResponseState.ANSWERED
    
    # 1 for standard, 1 for the single valid lab
    assert len(result.evidence) == 2
    
    lab_evidences = [e for e in result.evidence if e.source_type == "laboratory"]
    assert len(lab_evidences) == 1
    assert "Valid Lab" in lab_evidences[0].content
    assert "Expired Lab" not in str(lab_evidences)
    assert "Unrecognized Lab" not in str(lab_evidences)


@pytest.mark.asyncio
@patch("app.workflows.workflow2_lab.extract_attributes", new_callable=AsyncMock)
async def test_workflow2_normalizes_extracted_product_type(
    mock_extract: AsyncMock,
    db_session: Session,
) -> None:
    _set_gate_ready(True)
    mock_extract.return_value.product_type = "drinking water"

    concept = _seed_concept(db_session, "drinking water", "Food")
    std = _seed_standard(db_session, "IS 10500:2012", "Drinking Water")
    _seed_mapping(db_session, concept, std)

    lab = Laboratory(
        bis_entity_id="LAB-WATER",
        name="Water Lab",
        recognition_status="RECOGNIZED",
        scope="Testing as per IS 10500:2012",
        validity=date.today() + timedelta(days=30),
        location="Delhi",
    )
    std.laboratories.append(lab)
    db_session.add(lab)
    db_session.commit()

    chunks = [
        RagflowChunk(
            bis_entity_id=std.bis_entity_id,
            title=std.title,
            snippet="",
            similarity=0.95,
        )
    ]
    mock_client = MockRagflowClient(chunks=chunks)
    workflow = Workflow2Lab(session=db_session, ragflow_client=mock_client)  # type: ignore[arg-type]

    result = await workflow.run("Find a BIS lab for drinking water testing")

    assert result.state == ResponseState.ANSWERED
    assert result.decision is not None
    assert result.decision.standard == "IS 10500:2012"
    assert any("Water Lab" in evidence.content for evidence in result.evidence)


@pytest.mark.asyncio
async def test_workflow2_zero_eligible_labs(db_session: Session) -> None:
    _set_gate_ready(True)

    concept = _seed_concept(db_session, "cement", "Building")
    std = _seed_standard(db_session, "IS 269:2015", "OPC Cement")
    _seed_mapping(db_session, concept, std)
    
    # Only adding an expired lab
    lab_expired = Laboratory(
        bis_entity_id="LAB-009",
        name="Expired Cement Lab",
        recognition_status="RECOGNIZED",
        scope="IS 269:2015 cement testing",
        validity=date.today() - timedelta(days=10),
        location="Pune",
    )
    std.laboratories.append(lab_expired)
    db_session.add(lab_expired)
    db_session.commit()

    chunks = [
        RagflowChunk(
            bis_entity_id=std.bis_entity_id,
            title=std.title,
            snippet="",
            similarity=0.99,
        )
    ]
    mock_client = MockRagflowClient(chunks=chunks)
    workflow = Workflow2Lab(session=db_session, ragflow_client=mock_client)  # type: ignore[arg-type]

    result = await workflow.run("cement")

    # Should HANDOFF to BIS LIMS search since zero labs are eligible
    assert result.state == ResponseState.HANDOFF
    assert result.action is not None
    assert result.action.action_type == "search_lims"
    assert "lims.bis.gov.in" in result.action.destination_url


@pytest.mark.asyncio
async def test_workflow2_multiple_valid_labs(db_session: Session) -> None:
    _set_gate_ready(True)

    concept = _seed_concept(db_session, "steel", "Metals")
    std = _seed_standard(db_session, "IS 1786:2008", "TMT Bars")
    _seed_mapping(db_session, concept, std)

    lab_a = Laboratory(
        bis_entity_id="LAB-A",
        name="Lab A",
        recognition_status="RECOGNIZED",
        scope="IS 1786:2008 testing",
        validity=date.today() + timedelta(days=100),
        location="Kolkata",
    )
    lab_b = Laboratory(
        bis_entity_id="LAB-B",
        name="Lab B",
        recognition_status="RECOGNIZED",
        scope="Also IS 1786:2008 testing",
        validity=date.today() + timedelta(days=200),
        location="Bhilai",
    )
    std.laboratories.extend([lab_a, lab_b])
    db_session.add_all([lab_a, lab_b])
    db_session.commit()

    chunks = [
        RagflowChunk(
            bis_entity_id=std.bis_entity_id,
            title=std.title,
            snippet="",
            similarity=0.99,
        )
    ]
    mock_client = MockRagflowClient(chunks=chunks)
    workflow = Workflow2Lab(session=db_session, ragflow_client=mock_client)  # type: ignore[arg-type]

    result = await workflow.run("steel")

    assert result.state == ResponseState.ANSWERED
    
    lab_evidences = [e for e in result.evidence if e.source_type == "laboratory"]
    assert len(lab_evidences) == 2
    assert any("Lab A" in e.content for e in lab_evidences)
    assert any("Lab B" in e.content for e in lab_evidences)
