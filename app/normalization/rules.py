from typing import List
from app.db.models import CanonicalConcept
from app.core.entities import ExtractedAttributes

def filter_candidates(candidates: List[CanonicalConcept], attributes: ExtractedAttributes) -> List[CanonicalConcept]:
    """
    Filters or boosts candidate concepts using structured attributes.
    """
    if not candidates:
        return []
        
    # Simple rule-based filtering:
    # If the extracted product type matches the concept domain or name, keep it.
    # Since candidate retrieval doesn't exist yet, this is a basic implementation
    # to demonstrate the contract.
    filtered = []
    prod_type_lower = attributes.product_type.lower() if attributes.product_type else ""
    
    for candidate in candidates:
        candidate_name_lower = candidate.name.lower() if candidate.name else ""
        candidate_domain_lower = candidate.domain.lower() if candidate.domain else ""
        
        # Keep candidate if product type is found in name or domain, 
        # or if we have no meaningful product type to filter by.
        if not prod_type_lower or prod_type_lower in candidate_name_lower or prod_type_lower in candidate_domain_lower:
            filtered.append(candidate)
            
    # If our simple filter removed everything, return the original candidates as a fallback
    if not filtered and candidates:
        return candidates
        
    return filtered
