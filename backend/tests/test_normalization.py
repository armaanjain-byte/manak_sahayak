import pytest
from unittest.mock import patch, AsyncMock
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.db.session import Base
from app.db.models import CanonicalConcept, ConceptAlias
from app.core.entities import ExtractedAttributes
from app.normalization.vocabulary import lookup_concept
from app.normalization.resolver import extract_attributes
from app.normalization.rules import filter_candidates

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

def test_exact_concept_match(db_session: Session) -> None:
    # Setup
    concept = CanonicalConcept(
        bis_entity_id="C1",
        name="pressure cooker",
        domain="kitchenware"
    )
    db_session.add(concept)
    db_session.commit()

    # Exact match case-insensitive
    result = lookup_concept(db_session, "Pressure Cooker")
    assert result is not None
    assert result.name == "pressure cooker"

def test_alias_match(db_session: Session) -> None:
    # Setup
    concept = CanonicalConcept(
        bis_entity_id="C2",
        name="pressure cooker",
        domain="kitchenware"
    )
    db_session.add(concept)
    db_session.commit()

    alias = ConceptAlias(
        alias="cooker",
        language="en",
        concept_id=concept.id
    )
    db_session.add(alias)
    db_session.commit()

    # Alias match
    result = lookup_concept(db_session, "cooker")
    assert result is not None
    assert result.name == "pressure cooker"

def test_no_match_returns_none(db_session: Session) -> None:
    # Setup
    concept = CanonicalConcept(
        bis_entity_id="C3",
        name="helmet",
        domain="safety"
    )
    db_session.add(concept)
    db_session.commit()

    # No match
    result = lookup_concept(db_session, "shoes")
    assert result is None

    # Empty string
    assert lookup_concept(db_session, "") is None
    assert lookup_concept(db_session, "   ") is None

@pytest.mark.asyncio
@patch("app.generation.llm.LLMClient._generate", new_callable=AsyncMock)
async def test_extract_attributes(mock_generate: AsyncMock) -> None:
    # Set up mock response
    mock_generate.return_value = '''
    ```json
    {
        "product_type": "pressure cooker",
        "material": "stainless steel",
        "intended_use": "domestic",
        "is_imported": false,
        "technical_attributes": ["5 litre"]
    }
    ```
    '''
    query = "domestic stainless steel pressure cooker 5 litre"
    attrs = await extract_attributes(query)
    
    assert attrs.product_type == "pressure cooker"
    assert attrs.material == "stainless steel"
    assert attrs.intended_use == "domestic"
    assert attrs.is_imported is False
    assert "5 litre" in attrs.technical_attributes
    mock_generate.assert_called_once()

def test_filter_candidates() -> None:
    c1 = CanonicalConcept(name="pressure cooker", domain="kitchenware")
    c2 = CanonicalConcept(name="steel helmet", domain="safety")
    c3 = CanonicalConcept(name="gas stove", domain="kitchenware")
    
    candidates = [c1, c2, c3]
    
    # Filter by name match
    attrs1 = ExtractedAttributes(product_type="helmet")
    res1 = filter_candidates(candidates, attrs1)
    assert len(res1) == 1
    assert res1[0].name == "steel helmet"
    
    # Filter by domain match
    attrs2 = ExtractedAttributes(product_type="kitchenware")
    res2 = filter_candidates(candidates, attrs2)
    assert len(res2) == 2
    assert {c.name for c in res2} == {"pressure cooker", "gas stove"}
    
    # No match fallback (returns all)
    attrs3 = ExtractedAttributes(product_type="unknown")
    res3 = filter_candidates(candidates, attrs3)
    assert len(res3) == 3
