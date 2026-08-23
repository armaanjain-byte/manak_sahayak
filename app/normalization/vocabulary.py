from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models import CanonicalConcept, ConceptAlias

def lookup_concept(session: Session, raw_term: str) -> Optional[CanonicalConcept]:
    """
    Given a raw term string, return the matching CanonicalConcept if an
    exact or alias match exists, else None.
    """
    if not raw_term:
        return None
        
    term_lower = raw_term.lower().strip()
    
    # 1. Try exact match on CanonicalConcept name (case-insensitive)
    concept = session.query(CanonicalConcept).filter(
        func.lower(CanonicalConcept.name) == term_lower
    ).first()
    
    if concept:
        return concept
        
    # 2. Try alias match
    alias = session.query(ConceptAlias).filter(
        func.lower(ConceptAlias.alias) == term_lower
    ).first()
    
    if alias:
        return alias.canonical_concept
        
    return None
