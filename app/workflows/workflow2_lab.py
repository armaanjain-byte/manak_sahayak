"""
Workflow 2: Standard -> testing scope -> eligible laboratory.

Gated on A2. Requires strictly 100% current validity/recognition checks on
recommended laboratories.
"""
from datetime import date
from typing import List

from sqlalchemy.orm import Session

from app.actions.destinations import BIS_LIMS_URL
from app.core.entities import (
    Action,
    ClarificationRequest,
    Confidence,
    DecisionObject,
    Evidence,
)
from app.core.states import ResponseState
from app.db.models import ConceptStandardMapping, Laboratory, Standard
from app.gates.registry import is_ready
from app.normalization.resolver import extract_attributes
from app.normalization.vocabulary import lookup_concept
from app.retrieval.candidate_ranking import rank_candidates
from app.retrieval.ragflow_client import RagflowClient
from app.retrieval.structured import fetch_standard
from app.workflows.base import Workflow, WorkflowResult


class Workflow2Lab(Workflow):
    def __init__(
        self,
        session: Session,
        ragflow_client: RagflowClient,
    ) -> None:
        self.session = session
        self.ragflow_client = ragflow_client

    async def run(self, query: str) -> WorkflowResult:
        """
        Executes Workflow 2.
        """
        query = query.strip()
        if not query:
            return WorkflowResult(state=ResponseState.NOT_FOUND)

        gate_passed = is_ready("workflow_2")

        if not gate_passed:
            return await self._run_fallback(self.session, self.ragflow_client, query)

        return await self._run_standard(self.session, self.ragflow_client, query)

    async def _run_fallback(
        self,
        session: Session,
        ragflow_client: RagflowClient,
        query: str,
    ) -> WorkflowResult:
        """
        Bounded fallback (PARTIAL behavior): candidate retrieval + clarification/abstention.
        Does not return a definitive lab recommendation answer (ANSWERED).
        """
        attributes = extract_attributes(query)
        concept = lookup_concept(session, query)
        if concept is None:
            return WorkflowResult(state=ResponseState.NOT_FOUND)

        search_result = await ragflow_client.search(query=query)
        ranked_chunks = rank_candidates(search_result.chunks, attributes)

        mappings = session.query(ConceptStandardMapping).filter(
            ConceptStandardMapping.concept_id == concept.id,
            ConceptStandardMapping.validated.is_(True)
        ).all()
        mapped_standard_entity_ids = {m.standard.bis_entity_id for m in mappings if m.standard}

        candidate_chunks = [c for c in ranked_chunks if c.bis_entity_id in mapped_standard_entity_ids]

        resolved_standards: List[Standard] = []
        for chunk in candidate_chunks:
            std = fetch_standard(session, chunk.bis_entity_id)
            if std:
                resolved_standards.append(std)

        if not resolved_standards:
            return WorkflowResult(state=ResponseState.NOT_FOUND)

        # Same conservatism principle as workflow 1: unready gate -> CLARIFICATION
        options = [f"{s.is_number} - {s.title}" for s in resolved_standards]
        question = (
            "One candidate standard was found for your query, but full validation "
            "coverage for laboratory recommendations is not yet complete. Please confirm "
            "this is the standard you are asking about before we proceed:"
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
        Normal full-logic behavior when Gate A2 is ready.
        """
        attributes = extract_attributes(query)
        concept = lookup_concept(session, query)
        if concept is None:
            return WorkflowResult(state=ResponseState.NOT_FOUND)

        search_result = await ragflow_client.search(query=query)
        ranked_chunks = rank_candidates(search_result.chunks, attributes)

        mappings = session.query(ConceptStandardMapping).filter(
            ConceptStandardMapping.concept_id == concept.id,
            ConceptStandardMapping.validated.is_(True)
        ).all()
        mapped_standard_entity_ids = {m.standard.bis_entity_id for m in mappings if m.standard}

        candidate_chunks = [c for c in ranked_chunks if c.bis_entity_id in mapped_standard_entity_ids]

        resolved_standards: List[Standard] = []
        for chunk in candidate_chunks:
            std = fetch_standard(session, chunk.bis_entity_id)
            if std:
                resolved_standards.append(std)

        if not resolved_standards:
            return WorkflowResult(state=ResponseState.NOT_FOUND)

        # If multiple candidate standards remain, ask for clarification on the standard first
        if len(resolved_standards) > 1:
            options = [f"{s.is_number} - {s.title}" for s in resolved_standards]
            clarification = ClarificationRequest(
                question="Multiple candidate standards found. Please clarify which standard you are interested in for laboratory testing:",
                options=options,
            )
            return WorkflowResult(
                state=ResponseState.CLARIFICATION,
                clarification=clarification,
            )

        target_std = resolved_standards[0]

        # Fetch laboratories matching this standard's scope
        # Using LIKE as no join table is available
        all_labs = session.query(Laboratory).filter(
            Laboratory.scope.like(f"%{target_std.is_number}%")
        ).all()

        eligible_labs = []
        today = date.today()
        for lab in all_labs:
            # Strictly filter by recognition status and validity
            if lab.recognition_status != "RECOGNIZED":
                continue
            if lab.validity is None or lab.validity < today:
                continue
            eligible_labs.append(lab)

        if not eligible_labs:
            # Zero eligible labs -> HANDOFF to BIS LIMS search
            action = Action(
                action_type="search_lims",
                destination_url=BIS_LIMS_URL,
            )
            evidence = [
                Evidence(
                    source_id=target_std.bis_entity_id,
                    source_type="standard",
                    content=f"Standard: {target_std.is_number} - {target_std.title}. No eligible labs found.",
                    authoritative=True,
                )
            ]
            return WorkflowResult(
                state=ResponseState.HANDOFF,
                action=action,
                evidence=evidence,
            )

        # Multiple or single eligible labs -> ANSWERED with all listed
        decision = DecisionObject(
            standard=target_std.is_number,
            pathway="testing-laboratory",
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
        for lab in eligible_labs:
            evidence.append(
                Evidence(
                    source_id=lab.bis_entity_id,
                    source_type="laboratory",
                    content=f"Laboratory: {lab.name} (Status: {lab.recognition_status}, Validity: {lab.validity})",
                    authoritative=True,
                )
            )

        return WorkflowResult(
            state=ResponseState.ANSWERED,
            decision=decision,
            evidence=evidence,
        )
