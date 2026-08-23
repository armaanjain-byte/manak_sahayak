"""
Candidate ranking: score-based sort + attribute-match boosting.

Takes raw RAGFlow chunks and optional structured attributes from the
normalization phase and returns chunks ordered by boosted score.

Design: no candidates are dropped here — ranking only. The caller
(workflow) decides any score cutoff threshold.
"""
from typing import List

from app.core.entities import ExtractedAttributes
from app.retrieval.ragflow_client import RagflowChunk

# How much to add to similarity when the product type appears in the title.
_PRODUCT_TYPE_BOOST = 0.15


def rank_candidates(
    chunks: List[RagflowChunk],
    attributes: ExtractedAttributes,
) -> List[RagflowChunk]:
    """
    Return `chunks` sorted by a boosted relevance score (descending).

    Boosting rules:
    - +0.15 if `attributes.product_type` (case-insensitive) appears in chunk title.

    Future: add more boosting signals (material, scope match, etc.) as the
    normalization phase fills in more ExtractedAttributes fields.
    """
    prod_type_lower = attributes.product_type.lower() if attributes.product_type else ""

    def boosted_score(chunk: RagflowChunk) -> float:
        score = chunk.similarity
        if prod_type_lower and prod_type_lower in chunk.title.lower():
            score += _PRODUCT_TYPE_BOOST
        return score

    return sorted(chunks, key=boosted_score, reverse=True)
