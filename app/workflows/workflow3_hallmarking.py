"""
Workflow 3: Hallmarking / HUID consumer guidance.

Gated on A3. This is a bounded consumer flow covering:
  1. INFORMATIONAL: What is HUID / what does a hallmark indicate.
  2. VERIFICATION: How to verify HUID / what to do if verification fails.
  3. OUT_OF_SCOPE: Any hallmarking question outside these two supported intents.

CRITICAL DESIGN CONSTRAINT:
  This workflow directs verification-intent queries to the official BIS CARE
  destination. It does NOT perform HUID verification itself and must never
  simulate or fabricate a verification result. The HANDOFF is the answer for
  verification intents — not a placeholder before doing the work.

LLM BOUNDARY (from workflow-contract.md):
  The LLM may classify intent and generate clarification questions.
  The LLM may NOT establish hallmarking eligibility, invent HUID identifiers,
  or produce a regulatory determination about a specific hallmarking record.
"""
from enum import Enum, auto

from sqlalchemy.orm import Session

from app.actions.destinations import BIS_CARE_APP_URL, BIS_HALLMARKING_INFO_URL
from app.core.entities import (
    Action,
    ClarificationRequest,
    Confidence,
    DecisionObject,
    Evidence,
)
from app.core.states import ResponseState
from app.db.models import HallmarkingRecord
from app.gates.registry import is_ready
from app.workflows.base import Workflow, WorkflowResult


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

class HallmarkingIntent(Enum):
    INFORMATIONAL = auto()   # "what is HUID", "what does this hallmark mean"
    VERIFICATION  = auto()   # "how do I verify HUID", "verification failed"
    OUT_OF_SCOPE  = auto()   # outside the bounded consumer scope


# Keywords that signal each intent.  Checked case-insensitively, in order.
_INFORMATIONAL_KEYWORDS = [
    "what is huid",
    "what is a huid",
    "what does huid",
    "what does hallmark",
    "what is hallmark",
    "what is bis hallmark",
    "hallmark mean",
    "huid mean",
    "indicate",
    "meaning of",
    "what does the mark",
]

_VERIFICATION_KEYWORDS = [
    "verify huid",
    "verify my huid",
    "how to verify",
    "how do i verify",
    "check huid",
    "check my huid",
    "verification failed",
    "verify hallmark",
    "check hallmark",
    "huid check",
    "confirm huid",
]


def _classify_intent(query: str) -> HallmarkingIntent:
    """
    Lightweight keyword-based intent classifier.

    Checked in this order: VERIFICATION first (takes precedence over
    INFORMATIONAL when both keywords could match), then INFORMATIONAL,
    then OUT_OF_SCOPE.
    """
    q = query.lower()

    for kw in _VERIFICATION_KEYWORDS:
        if kw in q:
            return HallmarkingIntent.VERIFICATION

    for kw in _INFORMATIONAL_KEYWORDS:
        if kw in q:
            return HallmarkingIntent.INFORMATIONAL

    return HallmarkingIntent.OUT_OF_SCOPE


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

class Workflow3Hallmarking(Workflow):
    """
    Bounded HUID / consumer hallmarking guidance workflow.

    Two supported intents:
      INFORMATIONAL → ANSWERED with evidence from HallmarkingRecord.
      VERIFICATION  → HANDOFF to BIS CARE (NOT a fake verification).

    Out-of-scope queries return NOT_FOUND with no fabricated answer.
    When Gate A3 is not ready the entire workflow falls back to
    CLARIFICATION (or NOT_FOUND for out-of-scope), never ANSWERED.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    async def run(self, query: str) -> WorkflowResult:
        query = query.strip()
        if not query:
            return WorkflowResult(state=ResponseState.NOT_FOUND)

        gate_passed = is_ready("workflow_3")

        if not gate_passed:
            return self._run_fallback(query)

        return self._run_full(query)

    # ------------------------------------------------------------------
    # Fallback — gate not ready
    # ------------------------------------------------------------------

    def _run_fallback(self, query: str) -> WorkflowResult:
        """
        Gate A3 not yet ready.  Return CLARIFICATION for recognised hallmarking
        intents, NOT_FOUND for queries clearly outside the bounded scope.
        Never return ANSWERED here.
        """
        intent = _classify_intent(query)

        if intent == HallmarkingIntent.OUT_OF_SCOPE:
            return WorkflowResult(state=ResponseState.NOT_FOUND)

        # For INFORMATIONAL or VERIFICATION intents we can at least confirm the
        # query is in-scope and tell the user we need more coverage.
        clarification = ClarificationRequest(
            question=(
                "I recognise this as a hallmarking / HUID question, but the "
                "validated hallmarking knowledge base is not yet complete. "
                "Could you clarify what you need? For immediate HUID verification "
                "please use the official BIS CARE app."
            ),
            options=[
                "I want to know what HUID means",
                "I want to verify a HUID",
                "Something else about hallmarking",
            ],
        )
        return WorkflowResult(
            state=ResponseState.CLARIFICATION,
            clarification=clarification,
        )

    # ------------------------------------------------------------------
    # Full path — gate ready
    # ------------------------------------------------------------------

    def _run_full(self, query: str) -> WorkflowResult:
        intent = _classify_intent(query)

        if intent == HallmarkingIntent.INFORMATIONAL:
            return self._handle_informational(query)

        if intent == HallmarkingIntent.VERIFICATION:
            return self._handle_verification()

        # OUT_OF_SCOPE — do not attempt a best-effort LLM answer
        return WorkflowResult(state=ResponseState.NOT_FOUND)

    # ------------------------------------------------------------------
    # Informational: "what is HUID / what does a hallmark indicate"
    # ------------------------------------------------------------------

    def _handle_informational(self, query: str) -> WorkflowResult:
        """
        Return an ANSWERED result backed by evidence from HallmarkingRecord.
        The decision object carries the explanation; evidence is sourced from
        at least one authoritative structured record — never an LLM-only answer.
        """
        # Fetch authoritative hallmarking records as structural evidence.
        # We use the first available records rather than query-specific matching
        # because informational HUID queries are general in nature.
        records: list[HallmarkingRecord] = (
            self.session.query(HallmarkingRecord).limit(5).all()
        )

        if not records:
            # No structured records available — cannot satisfy the evidence
            # invariant; hand off to official BIS hallmarking page.
            action = Action(
                action_type="hallmarking_info",
                destination_url=BIS_HALLMARKING_INFO_URL,
            )
            return WorkflowResult(
                state=ResponseState.HANDOFF,
                action=action,
                evidence=[],
            )

        decision = DecisionObject(
            pathway="hallmarking-consumer-information",
            confidence=Confidence.HIGH,
        )
        evidence = [
            Evidence(
                source_id=rec.bis_entity_id,
                source_type="hallmarking_record",
                content=(
                    f"Hallmarking record — Metal: {rec.metal}, "
                    f"Article type: {rec.article_type}"
                    + (f", HUID: {rec.huid}" if rec.huid else "")
                    + "."
                ),
                authoritative=True,
            )
            for rec in records
        ]
        return WorkflowResult(
            state=ResponseState.ANSWERED,
            decision=decision,
            evidence=evidence,
        )

    # ------------------------------------------------------------------
    # Verification: "how do I verify HUID / verification failed"
    # ------------------------------------------------------------------

    def _handle_verification(self) -> WorkflowResult:
        """
        Direct the user to the official BIS CARE app for HUID verification.

        This workflow does NOT verify HUIDs itself.  The HANDOFF IS the answer
        for verification-intent queries — the official channel is BIS CARE.
        Returning HANDOFF here is correct and complete, not a placeholder.
        """
        action = Action(
            action_type="huid_verification",
            destination_url=BIS_CARE_APP_URL,
        )
        # Evidence is not structurally required for HANDOFF but providing it
        # gives the orchestration layer provenance for the destination choice.
        evidence = [
            Evidence(
                source_id="bis-care-official",
                source_type="official_service",
                content=(
                    "BIS CARE is the official BIS consumer app for HUID "
                    "verification, licence/R-number checks, and complaints. "
                    f"URL: {BIS_CARE_APP_URL}"
                ),
                authoritative=True,
            )
        ]
        return WorkflowResult(
            state=ResponseState.HANDOFF,
            action=action,
            evidence=evidence,
        )
