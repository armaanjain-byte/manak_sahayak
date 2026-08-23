"""
Workflow 1: Product -> Standard -> QCO -> mandatory status -> supported pathway.

Flagship workflow implementation following the core UX contract:
Answer -> Evidence -> Action.

Enforces state invariants, data/security boundary, and gate criteria.
"""
from typing import Any, List, Optional
from sqlalchemy.orm import Session

from app.workflows.base import Workflow, WorkflowResult
from app.core.states import ResponseState
from app.core.entities import (
    DecisionObject,
    Evidence,
    ClarificationRequest,
    Confidence,
)
from app.db.models import Standard, ConceptStandardMapping
from app.gates.registry import is_ready
from app.normalization.resolver import extract_attributes
from app.normalization.vocabulary import lookup_concept
from app.normalization.rules import filter_candidates
from app.retrieval.ragflow_client import RagflowClient
from app.retrieval.candidate_ranking import rank_candidates
from app.retrieval.structured import fetch_standard


class Workflow1StandardQCO(Workflow):
    """
    Workflow 1 resolves a query for a product into standard, QCO, mandatory
    status, and supported pathway.
    
    Supports dependency injection for session and RAGFlow client to remain
    fully offline-testable.
    """

    def __init__(
        self,
        session: Optional[Session] = None,
        ragflow_client: Optional[Any] = None,
    ) -> None:
        self.session = session
        self.ragflow_client = ragflow_client

    async def run(self, context: Any) -> WorkflowResult:
        # 1. Resolve dependencies and query
        session = self.session
        if session is None:
            if isinstance(context, dict):
                session = context.get("session")
            elif hasattr(context, "session"):
                session = getattr(context, "session")

        if session is None:
            raise ValueError("Database session is required to run Workflow1.")

        ragflow_client = self.ragflow_client
        if ragflow_client is None:
            if isinstance(context, dict):
                ragflow_client = context.get("ragflow_client")
            elif hasattr(context, "ragflow_client"):
                ragflow_client = getattr(context, "ragflow_client")

        if ragflow_client is None:
            ragflow_client = RagflowClient()

        query = ""
        if isinstance(context, str):
            query = context
        elif isinstance(context, dict):
            query = context.get("query", "")
        elif hasattr(context, "query"):
            query = getattr(context, "query")

        query = query.strip()
        if not query:
            return WorkflowResult(state=ResponseState.NOT_FOUND)

        # 2. Check gate readiness
        # Note: app.gates.registry expects "workflow_1" as registered in WORKFLOW_CRITERIA
        gate_passed = is_ready("workflow_1")

        if not gate_passed:
            return await self._run_fallback(session, ragflow_client, query)

        return await self._run_standard(session, ragflow_client, query)

    async def _run_fallback(
        self,
        session: Session,
        ragflow_client: RagflowClient,
        query: str,
    ) -> WorkflowResult:
        """
        Bounded fallback (PARTIAL behavior): candidate retrieval + clarification/abstention.
        Does not return a definitive compliance answer (ANSWERED) — not even for a single
        matching candidate, because the A1 gate is what certifies the validated-mappings
        coverage is sufficient for a trustworthy conclusion.

        Why we still query ConceptStandardMapping.validated.is_(True) here:
        Individual validated=True rows are set per-mapping as each ingestion run confirms
        a product→standard link is correct. A1 does not gate that per-row validity — it
        gates *count* (≥20 validated_standard_mappings and ≥10 validated_qco_mappings).
        A mapping that already exists and is marked validated is individually trustworthy;
        what A1 certifies is that the *corpus is wide enough* to support authoritative
        answers. In the fallback we therefore use those mappings as a candidate signal
        (they are the best unambiguous pointer we have), but we surface them as unconfirmed
        candidates requiring user clarification — never as a resolved answer — regardless
        of how many come back.
        """
        # A1 normalization flow - normalize term to CanonicalConcept
        attributes = extract_attributes(query)
        concept = lookup_concept(session, query)
        if concept is None:
            return WorkflowResult(state=ResponseState.NOT_FOUND)

        # Semantic retrieval
        search_result = await ragflow_client.search(query=query)
        ranked_chunks = rank_candidates(search_result.chunks, attributes)

        # Use individually-validated ConceptStandardMapping rows as a candidate signal.
        # See docstring above for why this is coherent when A1 is unready.
        mappings = session.query(ConceptStandardMapping).filter(
            ConceptStandardMapping.concept_id == concept.id,
            ConceptStandardMapping.validated.is_(True)
        ).all()
        mapped_standard_entity_ids = {m.standard.bis_entity_id for m in mappings if m.standard}

        # Intersect semantic candidates with individually-validated mappings
        candidate_chunks = [c for c in ranked_chunks if c.bis_entity_id in mapped_standard_entity_ids]

        resolved_standards: List[Standard] = []
        for chunk in candidate_chunks:
            std = fetch_standard(session, chunk.bis_entity_id)
            if std:
                resolved_standards.append(std)

        if not resolved_standards:
            return WorkflowResult(state=ResponseState.NOT_FOUND)

        # Whether we found one candidate or many, present all as unconfirmed options.
        # The A1 gate is not yet satisfied, so we must not assert that any one standard
        # is the correct answer — even if only one came back. The user must confirm.
        options = [f"{s.is_number} - {s.title}" for s in resolved_standards]
        question = (
            "One candidate standard was found for your query, but full validation "
            "coverage is not yet complete. Please confirm this is the standard you "
            "are asking about before we proceed:"
            if len(resolved_standards) == 1
            else "Multiple candidate standards were found. Please clarify which standard you are interested in:"
        )
        clarification = ClarificationRequest(
            question=question,
            options=options,
        )
        return WorkflowResult(
            state=ResponseState.CLARIFICATION,
            clarification=clarification,
        )

    async def _run_standard(
        self,
        session: Session,
        ragflow_client: RagflowClient,
        query: str,
    ) -> WorkflowResult:
        """
        Normal full-logic behavior when Gate A1 is ready.
        """
        # Step a/b: attributes extraction and normalization to concept
        attributes = extract_attributes(query)
        concept = lookup_concept(session, query)
        if concept is None:
            return WorkflowResult(state=ResponseState.NOT_FOUND)

        # Step d: Call filter_candidates to filter/boost concepts
        filtered_concepts = filter_candidates([concept], attributes)
        if not filtered_concepts:
            return WorkflowResult(state=ResponseState.NOT_FOUND)

        # Step c: semantic candidate standards retrieval
        search_result = await ragflow_client.search(query=query)
        ranked_chunks = rank_candidates(search_result.chunks, attributes)

        # Map concept to its valid standards in the database
        mappings = session.query(ConceptStandardMapping).filter(
            ConceptStandardMapping.concept_id == concept.id,
            ConceptStandardMapping.validated.is_(True)
        ).all()
        mapped_standard_entity_ids = {m.standard.bis_entity_id for m in mappings if m.standard}

        # Filter candidates based on database mappings
        candidate_chunks = [c for c in ranked_chunks if c.bis_entity_id in mapped_standard_entity_ids]

        resolved_standards: List[Standard] = []
        for chunk in candidate_chunks:
            std = fetch_standard(session, chunk.bis_entity_id)
            if std:
                resolved_standards.append(std)

        if not resolved_standards:
            return WorkflowResult(state=ResponseState.NOT_FOUND)

        # Step e: If multiple candidates remain, return CLARIFICATION
        if len(resolved_standards) > 1:
            options = [f"{s.is_number} - {s.title}" for s in resolved_standards]
            clarification = ClarificationRequest(
                question="Multiple candidate standards found. Please clarify which standard you are interested in:",
                options=options,
            )
            return WorkflowResult(
                state=ResponseState.CLARIFICATION,
                clarification=clarification,
            )

        # Step f: exactly one resolved standard
        target_std = resolved_standards[0]
        qcos = target_std.qcos

        # Step g: If evidence conflicts (different QCO mandatory statuses), return CONFLICT
        if len(qcos) >= 2:
            mandatory_statuses = {q.mandatory for q in qcos}
            if len(mandatory_statuses) > 1:
                evidence = [
                    Evidence(
                        source_id=q.bis_entity_id,
                        source_type="qco",
                        content=f"QCO {q.qco_identifier}: mandatory={q.mandatory}",
                        authoritative=True,
                    )
                    for q in qcos
                ]
                return WorkflowResult(
                    state=ResponseState.CONFLICT,
                    evidence=evidence,
                )

        # Normal single match case -> ANSWERED
        qco = qcos[0] if qcos else None
        
        mandatory = qco.mandatory if qco else False
        basis = qco.qco_identifier if qco else None
        effective_from = str(qco.effective_from) if (qco and qco.effective_from) else None

        decision = DecisionObject(
            standard=target_std.is_number,
            mandatory=mandatory,
            basis=basis,
            effective_from=effective_from,
            pathway="supported-scheme",
            confidence=Confidence.HIGH,
        )

        evidence = [
            Evidence(
                source_id=target_std.bis_entity_id,
                source_type="standard",
                content=f"Standard: {target_std.is_number} - {target_std.title}",
                authoritative=True,
            )
        ]
        if qco:
            evidence.append(
                Evidence(
                    source_id=qco.bis_entity_id,
                    source_type="qco",
                    content=f"QCO: {qco.qco_identifier}. Category: {qco.product_category}.",
                    authoritative=True,
                )
            )

        return WorkflowResult(
            state=ResponseState.ANSWERED,
            decision=decision,
            evidence=evidence,
        )
