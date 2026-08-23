"""
Tests for Workflow 3 (Hallmarking / HUID consumer guidance).

All tests are fully offline — no live Postgres or BIS CARE connection required.

Key contract being tested:
  - Gate NOT ready -> CLARIFICATION or NOT_FOUND, never ANSWERED.
  - INFORMATIONAL intent -> ANSWERED with evidence from HallmarkingRecord.
  - VERIFICATION intent -> HANDOFF to BIS CARE, never a fake verification.
  - OUT_OF_SCOPE intent -> NOT_FOUND, no fabricated answer.
"""
import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.states import ResponseState
from app.db.models import HallmarkingRecord
from app.db.session import Base
from app.gates.registry import registry as global_registry
from app.actions.destinations import BIS_CARE_APP_URL
from app.workflows.workflow3_hallmarking import Workflow3Hallmarking


# ---------------------------------------------------------------------------
# Fixtures
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


def _set_gate_ready(ready: bool) -> None:
    if ready:
        global_registry.update_metrics(
            "workflow_3",
            {
                "validated_huid_flows": 6,
                "authoritative_evidence_records_mapped": 15,
                "successful_e2e_consumer_queries": 10,
                "verified_official_handoffs": 2,
            },
        )
    else:
        global_registry.update_metrics("workflow_3", {})


def _seed_hallmarking_records(session: Session) -> list[HallmarkingRecord]:
    records = [
        HallmarkingRecord(
            bis_entity_id="HM-GOLD-001",
            metal="Gold",
            article_type="Ring",
            huid="HUID-AAABBB",
            jeweller_registration="REG-001",
            source_url="https://example.com/hm001",
        ),
        HallmarkingRecord(
            bis_entity_id="HM-SILVER-002",
            metal="Silver",
            article_type="Bracelet",
            huid=None,
            source_url="https://example.com/hm002",
        ),
    ]
    session.add_all(records)
    session.commit()
    return records


# ---------------------------------------------------------------------------
# Tests — gate not ready
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workflow3_gate_not_ready_informational_returns_clarification(
    db_session: Session,
) -> None:
    """Gate A3 not ready: informational HUID query -> CLARIFICATION, never ANSWERED."""
    _set_gate_ready(False)
    _seed_hallmarking_records(db_session)
    workflow = Workflow3Hallmarking(session=db_session)

    result = await workflow.run("what is HUID")

    assert result.state == ResponseState.CLARIFICATION
    assert result.clarification is not None
    assert result.decision is None, "Gate not ready must not produce a decision"


@pytest.mark.asyncio
async def test_workflow3_gate_not_ready_verification_returns_clarification(
    db_session: Session,
) -> None:
    """Gate A3 not ready: verification HUID query -> CLARIFICATION, never ANSWERED."""
    _set_gate_ready(False)
    workflow = Workflow3Hallmarking(session=db_session)

    result = await workflow.run("how do I verify HUID")

    assert result.state == ResponseState.CLARIFICATION
    assert result.clarification is not None
    assert result.decision is None


@pytest.mark.asyncio
async def test_workflow3_gate_not_ready_out_of_scope_returns_not_found(
    db_session: Session,
) -> None:
    """Gate A3 not ready: out-of-scope query -> NOT_FOUND."""
    _set_gate_ready(False)
    workflow = Workflow3Hallmarking(session=db_session)

    result = await workflow.run("what is the hallmarking policy for exporters")

    assert result.state == ResponseState.NOT_FOUND
    assert result.decision is None


# ---------------------------------------------------------------------------
# Tests — gate ready: informational intent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workflow3_informational_returns_answered_with_evidence(
    db_session: Session,
) -> None:
    """'What is HUID' -> ANSWERED with HallmarkingRecord evidence."""
    _set_gate_ready(True)
    _seed_hallmarking_records(db_session)
    workflow = Workflow3Hallmarking(session=db_session)

    result = await workflow.run("what is HUID")

    assert result.state == ResponseState.ANSWERED
    assert result.decision is not None
    # Evidence invariant: at least one authoritative item
    authoritative = [e for e in result.evidence if e.authoritative]
    assert len(authoritative) >= 1
    # All evidence must come from HallmarkingRecord
    for ev in result.evidence:
        assert ev.source_type == "hallmarking_record"


@pytest.mark.asyncio
async def test_workflow3_informational_what_does_hallmark_indicate(
    db_session: Session,
) -> None:
    """'What does this hallmark indicate' -> ANSWERED."""
    _set_gate_ready(True)
    _seed_hallmarking_records(db_session)
    workflow = Workflow3Hallmarking(session=db_session)

    result = await workflow.run("what does this hallmark indicate")

    assert result.state == ResponseState.ANSWERED
    assert any(e.authoritative for e in result.evidence)


@pytest.mark.asyncio
async def test_workflow3_informational_no_records_handoffs(
    db_session: Session,
) -> None:
    """When gate is ready but there are no HallmarkingRecords -> HANDOFF to BIS info page."""
    _set_gate_ready(True)
    # No records seeded
    workflow = Workflow3Hallmarking(session=db_session)

    result = await workflow.run("what is HUID")

    # Cannot satisfy ANSWERED evidence invariant without records; must HANDOFF
    assert result.state == ResponseState.HANDOFF
    assert result.action is not None
    assert "hallmarking" in result.action.destination_url


# ---------------------------------------------------------------------------
# Tests — gate ready: verification intent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workflow3_verification_returns_handoff_to_bis_care(
    db_session: Session,
) -> None:
    """
    'How do I verify HUID' -> HANDOFF to official BIS CARE destination.

    Critical invariant: this workflow does NOT perform verification.
    The HANDOFF state IS the complete answer for verification intents.
    The destination must be the official BIS CARE URL, not a fabricated result.
    """
    _set_gate_ready(True)
    workflow = Workflow3Hallmarking(session=db_session)

    result = await workflow.run("how do I verify HUID")

    assert result.state == ResponseState.HANDOFF
    assert result.action is not None
    assert result.action.destination_url == BIS_CARE_APP_URL
    assert result.action.action_type == "huid_verification"
    # Must NOT produce a decision (that would imply we verified something)
    assert result.decision is None


@pytest.mark.asyncio
async def test_workflow3_verification_failed_returns_handoff(
    db_session: Session,
) -> None:
    """'Verification failed' -> HANDOFF to BIS CARE, not a fabricated outcome."""
    _set_gate_ready(True)
    workflow = Workflow3Hallmarking(session=db_session)

    result = await workflow.run("my HUID verification failed what do I do")

    assert result.state == ResponseState.HANDOFF
    assert result.action is not None
    assert result.action.destination_url == BIS_CARE_APP_URL
    assert result.decision is None


# ---------------------------------------------------------------------------
# Tests — gate ready: out of scope
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workflow3_out_of_scope_returns_not_found(
    db_session: Session,
) -> None:
    """Out-of-scope hallmarking question -> NOT_FOUND, never a guessed answer."""
    _set_gate_ready(True)
    workflow = Workflow3Hallmarking(session=db_session)

    result = await workflow.run("what is the hallmarking fee for A&H centres")

    assert result.state == ResponseState.NOT_FOUND
    assert result.decision is None


@pytest.mark.asyncio
async def test_workflow3_empty_query_returns_not_found(
    db_session: Session,
) -> None:
    """Empty query -> NOT_FOUND."""
    _set_gate_ready(True)
    workflow = Workflow3Hallmarking(session=db_session)

    result = await workflow.run("   ")

    assert result.state == ResponseState.NOT_FOUND
