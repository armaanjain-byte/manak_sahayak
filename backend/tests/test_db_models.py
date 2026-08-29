import pytest
from typing import Generator
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.db.session import Base
from app.db.models import (
    Standard,
    QCO,
    QCOStandardMapping,
    Laboratory,
    HallmarkingRecord,
    CanonicalConcept,
    ConceptAlias,
    ConceptStandardMapping,
)

# We use an in-memory SQLite database ('sqlite:///:memory:') for unit tests.
# Rationale: This allows tests to run instantly during local development and in the CI pipeline
# without requiring an external PostgreSQL instance or Docker container, ensuring a fast
# and completely isolated test environment.
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

def test_standard_model_roundtrip(db_session: Session) -> None:
    now = datetime.now()
    standard = Standard(
        bis_entity_id="IS-1234:2021",
        is_number="IS 1234:2021",
        title="Test Standard Title",
        scope="This standard covers testing of widgets.",
        status="ACTIVE",
        revision="2021",
        related_standards=["IS 4321:2020", "IS 5678:2019"],
        source_url="https://example.com/is1234",
        retrieved_at=now,
    )
    db_session.add(standard)
    db_session.commit()

    retrieved = db_session.query(Standard).filter_by(bis_entity_id="IS-1234:2021").first()
    assert retrieved is not None
    assert retrieved.is_number == "IS 1234:2021"
    assert retrieved.title == "Test Standard Title"
    assert retrieved.scope == "This standard covers testing of widgets."
    assert retrieved.status == "ACTIVE"
    assert retrieved.revision == "2021"
    assert retrieved.related_standards == ["IS 4321:2020", "IS 5678:2019"]
    assert retrieved.source_url == "https://example.com/is1234"
    # Compare datetime within small delta due to DB resolution
    assert retrieved.retrieved_at is not None
    assert abs((retrieved.retrieved_at - now).total_seconds()) < 1.0

def test_qco_model_roundtrip(db_session: Session) -> None:
    now = datetime.now()
    pub_date = date(2026, 1, 1)
    amendment_date = date(2026, 3, 1)
    eff_date = date(2026, 6, 1)
    qco = QCO(
        bis_entity_id="QCO-2026-001",
        qco_identifier="QCO-1234",
        product_category="Widgets",
        ministry="Ministry of Consumer Affairs",
        publication_date=pub_date,
        amendment_date=amendment_date,
        effective_from=eff_date,
        mandatory=True,
        exemptions="Exempts micro-enterprises.",
        source_url="https://example.com/qco1234",
        retrieved_at=now,
    )
    db_session.add(qco)
    db_session.commit()

    retrieved = db_session.query(QCO).filter_by(bis_entity_id="QCO-2026-001").first()
    assert retrieved is not None
    assert retrieved.qco_identifier == "QCO-1234"
    assert retrieved.product_category == "Widgets"
    assert retrieved.ministry == "Ministry of Consumer Affairs"
    assert retrieved.publication_date == pub_date
    assert retrieved.amendment_date == amendment_date
    assert retrieved.effective_from == eff_date
    assert retrieved.mandatory is True
    assert retrieved.exemptions == "Exempts micro-enterprises."
    assert retrieved.source_url == "https://example.com/qco1234"
    assert retrieved.retrieved_at is not None
    assert abs((retrieved.retrieved_at - now).total_seconds()) < 1.0

def test_qco_standard_many_to_many_relationship(db_session: Session) -> None:
    standard = Standard(
        bis_entity_id="IS-1234:2021",
        is_number="IS 1234:2021",
        title="Test Standard Title",
        scope="Testing scope",
        status="ACTIVE",
    )
    qco = QCO(
        bis_entity_id="QCO-2026-001",
        qco_identifier="QCO-1234",
        product_category="Widgets",
        ministry="Ministry of Consumer Affairs",
        mandatory=True,
    )
    
    db_session.add(standard)
    db_session.add(qco)
    db_session.commit()

    # Link standard and QCO through join table
    mapping = QCOStandardMapping(
        qco_bis_entity_id="QCO-2026-001",
        standard_bis_entity_id="IS-1234:2021",
    )
    db_session.add(mapping)
    db_session.commit()

    # Test relationship mapping
    retrieved_qco = db_session.query(QCO).filter_by(bis_entity_id="QCO-2026-001").first()
    assert retrieved_qco is not None
    assert len(retrieved_qco.standards) == 1
    assert retrieved_qco.standards[0].bis_entity_id == "IS-1234:2021"

    retrieved_std = db_session.query(Standard).filter_by(bis_entity_id="IS-1234:2021").first()
    assert retrieved_std is not None
    assert len(retrieved_std.qcos) == 1
    assert retrieved_std.qcos[0].bis_entity_id == "QCO-2026-001"

def test_laboratory_model_roundtrip(db_session: Session) -> None:
    now = datetime.now()
    val_date = date(2027, 12, 31)
    lab = Laboratory(
        bis_entity_id="LAB-999",
        name="National Testing Lab",
        recognition_status="RECOGNIZED",
        scope="Chemical testing of polymers.",
        validity=val_date,
        location="New Delhi",
        source_url="https://example.com/lab999",
        retrieved_at=now,
    )
    db_session.add(lab)
    db_session.commit()

    retrieved = db_session.query(Laboratory).filter_by(bis_entity_id="LAB-999").first()
    assert retrieved is not None
    assert retrieved.name == "National Testing Lab"
    assert retrieved.recognition_status == "RECOGNIZED"
    assert retrieved.scope == "Chemical testing of polymers."
    assert retrieved.validity == val_date
    assert retrieved.location == "New Delhi"
    assert retrieved.source_url == "https://example.com/lab999"
    assert retrieved.retrieved_at is not None
    assert abs((retrieved.retrieved_at - now).total_seconds()) < 1.0

def test_hallmarking_record_model_roundtrip(db_session: Session) -> None:
    now = datetime.now()
    record = HallmarkingRecord(
        bis_entity_id="HM-GOLD-111",
        metal="Gold",
        article_type="Ring",
        huid="HUID123456",
        jeweller_registration="REG-777",
        source_url="https://example.com/hm111",
        retrieved_at=now,
    )
    db_session.add(record)
    db_session.commit()

    retrieved = db_session.query(HallmarkingRecord).filter_by(bis_entity_id="HM-GOLD-111").first()
    assert retrieved is not None
    assert retrieved.metal == "Gold"
    assert retrieved.article_type == "Ring"
    assert retrieved.huid == "HUID123456"
    assert retrieved.jeweller_registration == "REG-777"
    assert retrieved.source_url == "https://example.com/hm111"
    assert retrieved.retrieved_at is not None
    assert abs((retrieved.retrieved_at - now).total_seconds()) < 1.0

def test_concept_alias_relationships(db_session: Session) -> None:
    concept = CanonicalConcept(
        bis_entity_id="CONCEPT-PRESSURE-COOKER",
        name="pressure cooker",
        domain="kitchenware",
    )
    db_session.add(concept)
    db_session.commit()

    alias_en = ConceptAlias(
        alias="cooker",
        language="en",
        concept_id=concept.id,
    )
    alias_hi = ConceptAlias(
        alias="कुकर",
        language="hi",
        concept_id=concept.id,
    )
    db_session.add(alias_en)
    db_session.add(alias_hi)
    db_session.commit()

    # Query concept and verify aliases relationship
    retrieved_concept = db_session.query(CanonicalConcept).filter_by(bis_entity_id="CONCEPT-PRESSURE-COOKER").first()
    assert retrieved_concept is not None
    assert len(retrieved_concept.aliases) == 2
    aliases_text = {a.alias for a in retrieved_concept.aliases}
    assert "cooker" in aliases_text
    assert "कुकर" in aliases_text

    # Cascade delete verification
    db_session.delete(retrieved_concept)
    db_session.commit()

    aliases_in_db = db_session.query(ConceptAlias).all()
    assert len(aliases_in_db) == 0

def test_concept_standard_mapping_relationship(db_session: Session) -> None:
    concept = CanonicalConcept(
        bis_entity_id="CONCEPT-PRESSURE-COOKER",
        name="pressure cooker",
        domain="kitchenware",
    )
    standard = Standard(
        bis_entity_id="IS-1234:2021",
        is_number="IS 1234:2021",
        title="Test Standard Title",
        scope="Testing scope",
        status="ACTIVE",
    )
    db_session.add(concept)
    db_session.add(standard)
    db_session.commit()

    mapping = ConceptStandardMapping(
        concept_id=concept.id,
        standard_id=standard.id,
        validated=True,
        notes="Validated mapping for prototype",
    )
    db_session.add(mapping)
    db_session.commit()

    # Verify mapping queries
    retrieved_mapping = db_session.query(ConceptStandardMapping).first()
    assert retrieved_mapping is not None
    assert retrieved_mapping.concept_id == concept.id
    assert retrieved_mapping.standard_id == standard.id
    assert retrieved_mapping.validated is True
    assert retrieved_mapping.notes == "Validated mapping for prototype"
    assert retrieved_mapping.canonical_concept.name == "pressure cooker"
    assert retrieved_mapping.standard.is_number == "IS 1234:2021"
