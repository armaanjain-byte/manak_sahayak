# Manak Sahayak — Product Requirements Document (v6)
## AI Reasoning & Orchestration Layer for Indian Standards & BIS Services
**SIH Problem Statement:** SIH26107  **Problem Statement Title:** AI-powered Intelligent Assistant for Indian Standards and BIS Services for Industries and Consumers  **Ministry:** Ministry of Consumer Affairs, Food & Public Distribution  **Department:** Department of Consumer Affairs (DoCA)  **Category:** Software  **Theme:** Smart Automation  **Document status:** Submission-ready PRD / scope-controlled prototype plan  **Revision:** v6 — independent workflow gates + final scope-freeze refinement  
---
## Executive Summary
Manak Sahayak is a natural-language reasoning and orchestration layer over BIS's existing information ecosystem. It is not a replacement for BIS portals or transactional systems. The user starts with a product, technical question, consumer question, or BIS-service need; Manak Sahayak determines the relevant intent and entities, retrieves supporting BIS evidence, applies bounded structured reasoning where required, explains the result, and hands the user to the correct official BIS destination.
The core technical contribution is not generic RAG. It is entity resolution and cross-source reasoning over heterogeneous BIS information: standards, QCOs, certification schemes, laboratory scopes/status, hallmarking guidance, and service information. The prototype intentionally builds three deep workflows and keeps the remaining service surface shallow but functional or explicitly future-state.
## Scope Status Legend
- **[BUILD]** — Implemented / demo-ready capability claimed by the team.
- **[PARTIAL]** — Implemented but deliberately bounded in depth, coverage, or domain.
- **[SPEC]** — Designed in the architecture/PRD, but not required to be fully implemented for the SIH demo.
- **[FUTURE]** — Post-hackathon product maturity or scale work.

---
## 1. Problem Statement
The Bureau of Indian Standards publishes a large standards and conformity-assessment ecosystem and operates multiple digital services for standards discovery, certification, laboratory information, hallmarking, consumer verification, complaints, and related services.
The practical user problem is not simply lack of information. BIS already provides substantial information through multiple portals, databases, apps, and documents. The problem is information orchestration: a user starts from an unstructured product or problem and may not know which BIS subsystem to open, what identifier to search, which source is authoritative for the question, or how to connect the resulting information into an actionable next step.
SIH26107 explicitly calls for an assistant that can answer questions on Indian Standards, recommend applicable standards, guide certification, explain certification processes, answer consumer queries, guide hallmarking, suggest relevant laboratories, answer technical queries, and support multilingual interaction.
## 2. Goals and Non-Goals
### Goals
- Convert natural-language questions/product descriptions into evidence-backed answers across BIS service domains.
- Ground every material factual/regulatory claim in authoritative evidence and abstain when evidence is insufficient.
- Make entity resolution + cross-source reasoning the technical centerpiece rather than generic document retrieval.
- Support multilingual interaction, with English + Hindi as the MVP and regulatory-entity preservation.

### Non-Goals
- No reproduction of full paywalled Indian Standard text.
- No replacement of BIS CARE, ManakOnline, LIMS, or other official transactional/verification systems.
- No claim that the assistant provides a final legal or compliance determination.
- No claim of full BIS-corpus coverage during the prototype. The evaluation corpus is intentionally bounded and representative.
- No automated production-grade freshness/re-ingestion pipeline required for the SIH demo.
- No full scheme taxonomy or exhaustive domain-specific rule coverage required for the SIH demo.

## 3. SIH Requirement Coverage
| SIH requirement | Product response | Status |
|---|---|---|
| Answer Indian Standard questions | User can ask natural-language questions and receive source-backed answers. | [BUILD] |
| Recommend applicable standards | Product description is normalized and mapped to ranked candidate standards. | [BUILD] — deep workflow |
| Certification guidance | Supported pathways map product/standard evidence to the relevant certification process. | [BUILD]/[PARTIAL] |
| Certification process explanation | Explain bounded supported process steps and hand off to official system. | [PARTIAL] |
| Consumer queries | Answer bounded consumer questions and route verification actions to BIS CARE/official services. | [PARTIAL] |
| Hallmarking | HUID and consumer hallmarking guidance. | [BUILD] — deep workflow |
| Testing laboratories | Find labs by standard/testing scope plus current recognition/validity. | [BUILD] — deep workflow |
| Technical queries | Answer from bounded public/permitted material; no unrestricted paywalled standard text. | [PARTIAL] |
| Multilingual interaction | English + Hindi MVP with preservation of regulatory entities. | [BUILD] |
| General BIS services | Bounded service registry and official handoff. | [PARTIAL] |

## 4. Target Users and Primary Jobs
| User | Primary job |
|---|---|
| MSME / Manufacturer | Which standard applies to my product? Is certification mandatory? What is my next step? |
| Consumer | What does this BIS mark/HUID mean? How do I verify it or proceed to the official service? |
| Procurement / Engineer | Which standard and testing requirements should I reference? |
| Jeweller / Hallmarking stakeholder | What hallmarking or HUID-related guidance applies? |

## 5. Competitive Landscape and Positioning
| Existing BIS system | What it already does | Manak Sahayak relationship |
|---|---|---|
| Know Your Standard | IS-number/keyword search; exposes standard-related documents/data, licences and laboratories for the selected standard. | Not replaced. Manak Sahayak starts from the user’s natural-language problem and routes into the relevant BIS evidence. |
| BIS CARE | Verification, HUID/R-number/licence functions, complaints, training, lab/office lookup, Know Your Standards, multilingual access. | Not replaced. Manak Sahayak provides conversational entry and cross-source reasoning, then hands off to BIS CARE when appropriate. |
| BIS LIMS | Laboratory recognition, scope, validity, status, and IS-wise lab discovery. | Not replaced. Manak Sahayak determines the relevant testing need and recommends eligible facilities before handoff. |
| Certification / FMCS / Hallmarking pages | Scheme/process-specific official documentation. | Not replaced. Manak Sahayak connects the user’s query to the relevant process and evidence. |

**Positioning:** BIS already contains substantial information and service functionality. The gap is information orchestration. Manak Sahayak is the natural-language entry point and reasoning layer that determines which BIS sources/services are relevant, connects them, explains the evidence, and hands the user to the official system.
## 6. Product Concept and Interaction Model
**Core UX contract: Answer → Evidence → Action.**

The assistant should not behave like an unconstrained generic chatbot. Each response should, where relevant, expose: (1) the answer/result, (2) supporting source evidence, (3) categorical confidence, and (4) the next official BIS action.
### Core intent classes
- Standard discovery
- Mandatory-status / QCO reasoning
- Certification guidance
- Laboratory discovery
- Hallmarking / HUID guidance
- Consumer queries
- Technical query
- General BIS service

## 7. Product Scope and Deep Workflow Strategy
| Workflow | Status | Depth | Scope |
|---|---|---|---|
| 1. Product → Standard → QCO → mandatory status → supported pathway | [BUILD — bounded coverage: ~40–60 curated concepts] | Deep within curated coverage | Entity extraction/normalization; candidate standard retrieval; applicability/scope match; QCO mapping; effective-date handling; supported scheme/pathway mapping; decision object; evidence; next action. Outside curated coverage: candidate retrieval only; ask clarification or abstain/handoff rather than infer a regulatory pathway. |
| 2. Standard → testing scope → eligible laboratory | [BUILD — validated standards only] | Deep within validated lab scope | Resolve standard; identify relevant testing scope; filter labs by scope, current recognition/status, and validity; present official lab evidence and LIMS handoff. Scope is limited to standards with validated testing-scope mappings in the prototype. |
| 3. Hallmarking → HUID / consumer guidance | [BUILD — bounded HUID/consumer coverage] | Deep within bounded workflow | Bounded hallmarking FAQs; HUID meaning/verification guidance; consumer action paths; official BIS CARE handoff. Unsupported hallmarking cases hand off to official BIS information/services rather than infer. |
| General BIS service Q&A | [PARTIAL] | Shallow | Bounded service registry, official links, eligibility/procedure summaries, handoff. |
| General technical Q&A | [PARTIAL] | Shallow | Bounded public/permitted source corpus; no unrestricted full-standard interpretation. |
| Full FMCS/AIR path, all scheme variants, full A&H-centre subsystem | [SPEC] | Future depth | Architecture supports extension; unsupported variants must hand off rather than guess. |

**Scope fence:** The demo goes deep on three workflows, but each [BUILD] claim is explicitly bounded by frozen validated coverage. Workflow 1 targets ~40–60 curated product concepts and is gated independently by A1; Workflow 2 covers only standards with validated lab-scope mappings and is gated by A2; Workflow 3 covers a bounded HUID/consumer workflow and is gated by A3. A slow vocabulary workstream does not block Workflows 2 or 3. Outside each workflow’s validated boundary, the system retrieves candidates where possible and otherwise asks for clarification, abstains, or hands off to the official BIS destination.

**Workflow readiness is independent:** A1 gates Workflow 1, A2 gates Workflow 2, and A3 gates Workflow 3. Orchestration requires at least two workflows to pass their gates; the full live “reasoning flagship” claim requires Workflow 1 to pass A1.
## 8. Intelligence Model and Decision Objects
### Processing chain
User query/product text
Entity extraction: product, material, use-case, manufacturer location, identifiers
Entity normalization: map user terms to BIS terminology
Candidate retrieval: structured store + document RAG
Applicability/scope matching
Bounded deterministic rules: QCO, mandatory status, effective date, supported pathway
Decision object
Confidence/abstention
LLM explanation

### Bounded rule types
| Rule | Purpose | Status |
|---|---|---|
| Scope applicability | Does the product description match the standard/QCO scope? | [BUILD] — bounded product domains |
| QCO mapping | Does an authoritative QCO regulate the candidate standard/product? | [BUILD] |
| Mandatory status | Is certification currently mandatory under the identified regulatory basis? | [BUILD] — bounded corpus |
| Effective date | Is the requirement current or upcoming based on effective date? | [BUILD] — bounded corpus |
| Limited exemptions | Does the indexed QCO include an explicit exception relevant to the query? | [PARTIAL] — only represented exemptions |
| Supported pathway | Which supported certification pathway applies to the resolved case? | [BUILD]/[PARTIAL] |
| Lab eligibility | Does a laboratory have relevant scope plus valid/current recognition status? | [BUILD] |
| Source conflict | Are authoritative sources conflicting or unresolved? | [BUILD] — abstention/handoff |
| Unsupported variant | Is this outside the prototype's supported scheme/domain coverage? | [BUILD] — handoff, not guessing |

### Decision object example
```json
{
  "standard": "IS-XXXXX:YYYY",
  "mandatory": true,
  "basis": "QCO-XXXX",
  "effective_from": "2026-09-01",
  "pathway": "supported-scheme",
  "confidence": "HIGH",
  "evidence": ["doc_id_123", "qco_id_456"]
}
```
### Confidence model
- **HIGH** — Authoritative evidence + clear entity/scope match + no unresolved conflict.
- **MEDIUM** — Strong evidence but some product ambiguity remains.
- **LOW** — Relevant evidence exists, but applicability is incomplete or weak.
- **INSUFFICIENT** — No adequate authoritative evidence, unresolved conflict, or unsupported variant; abstain or hand off.

## 9. Technical Architecture
```text
USER
  ↓
Language ID
  ↓
Intent Router
  ↓
Entity Extraction
  ↓
Entity Normalization
  ↓
┌──────────────────────┬──────────────────────┐
│ Structured BIS Store │ Document RAG         │
│ SQLite/Postgres      │ RAGFlow + BGE-M3     │
│                      │ + reranker            │
└──────────────┬───────┴──────────┬───────────┘
               ↓                   ↓
          Evidence Aggregation
               ↓
        Bounded Rule Engine
               ↓
       Decision + Confidence
               ↓
          LLM Explanation
               ↓
     Answer + Evidence + Action
               ↓
          Official BIS Handoff
```
### Architectural principles
- The LLM does not determine regulatory status.
- Structured facts are stored separately from unstructured documents.
- RAG is a retrieval substrate, not the product itself.
- Unsupported or ambiguous cases return clarification/abstention/handoff states.
- The action router points to official BIS services instead of reproducing their transactional workflows.

## 10. Data Model and Knowledge Sources
| Domain | Key fields | Prototype treatment |
|---|---|---|
| Standards | IS number, title, scope, status, revision, related standards | [BUILD] bounded corpus |
| QCO | product/category, standard, ministry, publication/effective date, exemptions | [BUILD] bounded corpus |
| Certification schemes | scheme type, eligibility, application/testing/inspection/renewal | [PARTIAL] supported variants only |
| Laboratories | name, recognition status, testing scope, validity, location | [BUILD] deep lab workflow |
| A&H Centres | name, recognition/registration status, location, hallmarking scope | [SPEC] except bounded hallmarking guidance |
| Hallmarking | metal, article type, jeweller registration, HUID, consumer verification | [BUILD] bounded HUID/consumer workflow |
| BIS services | service name, description, eligibility, official URL, last verified/retrieved | [PARTIAL] bounded registry |
| Consumer | FAQ, mark meaning, verification guidance | [PARTIAL] bounded corpus |

### Relationship model
A lightweight relational model is sufficient for the prototype. The design captures relationships such as QCO→Standard, Standard→Testing Scope, Testing Scope→Laboratory, Product→Candidate Standard, Product→Supported Pathway. A graph database is not required.
### Source metadata
Each imported record should carry, where available: source URL, source type, title/identifier, publication date, effective date, status/version, retrieved_at, and relationship metadata. This is metadata capture, not a claim of automated production freshness.

## 11. Source Hierarchy, Provenance and Evidence
### Source priority
1. Official BIS current page/database (including Know Your Standard, BIS CARE-linked official information, LIMS, scheme pages)
2. Official government notification / QCO / gazette
3. Official BIS guidance PDF
4. Secondary source only when explicitly flagged; not used as the primary regulatory basis

### Conflict handling
Prefer the currently applicable authoritative instrument after checking document type, amendment/supersession relationship, and effective date. Do not simply assume that the newest page is legally controlling. If the conflict cannot be resolved, return **Evidence conflict** or hand off.

### Citation policy
The prototype promises document-level references for material claims. Clause/section-level references are shown only when ingestion reliably preserves them. The system does not claim universal clause-level citation.

## 12. Multilingual Strategy
### MVP [BUILD]
Language identification → preserve regulatory entities/identifiers → multilingual retrieval → localized answer generation. IS numbers, QCO identifiers, HUID, scheme names, and other protected terms must not be blindly translated.
### V1 [SPEC]
Benchmark direct multilingual retrieval against translation-assisted retrieval before selecting a final production path. IndicTrans2 remains a candidate translation component, not the language-ID layer.

## 13. Feature Requirements
### MVP [BUILD]
- [ ] English + Hindi natural-language assistant
- [ ] Ranked standard discovery
- [ ] Scope/applicability matching
- [ ] QCO and mandatory-status reasoning for bounded corpus
- [ ] Supported certification-pathway guidance
- [ ] Laboratory discovery using scope + current recognition/status + validity
- [ ] Hallmarking/HUID consumer guidance
- [ ] Decision object + categorical confidence
- [ ] Citations for material claims
- [ ] Clarifying questions
- [ ] Explicit abstention
- [ ] Official BIS action handoff

### Partial / bounded [PARTIAL]
- [ ] General BIS service Q&A from bounded service registry
- [ ] General technical Q&A from public/permitted sources
- [ ] Consumer FAQ beyond the deep hallmarking flow

### V1 [SPEC]
- [ ] Additional regional languages
- [ ] India/foreign manufacturer entity for FMCS-aware branching
- [ ] Standard version/supersession comparison
- [ ] Compliance checklist generation
- [ ] Broader scheme taxonomy

### Future [FUTURE]
- [ ] Automated freshness/re-ingestion
- [ ] Full claim-level verification on every response
- [ ] Voice input
- [ ] Usage analytics
- [ ] Full A&H-centre discovery
- [ ] Formal expert-adjudicated benchmark at scale
- [ ] Full-depth FMCS/AIR workflow

## 14. User Experience and Response Contract
### Preferred answer structure
- **Answer / Result** — concise user-facing conclusion
- **Why** — the key reasoning chain or product-to-standard match
- **Evidence** — official source(s) supporting material claims
- **Confidence** — HIGH / MEDIUM / LOW / INSUFFICIENT
- **Next action** — official BIS service or clarification question

### Example compliance response
```text
RESULT
Mandatory

APPLICABLE STANDARD
IS XXXXX:YYYY

REGULATORY BASIS
QCO-XXXX

EFFECTIVE
DD/MM/YYYY

SUPPORTED PATHWAY
Scheme / pathway supported by prototype

WHY
The normalized product attributes match the indexed scope.

EVIDENCE
Official BIS/QCO sources

CONFIDENCE
HIGH

NEXT ACTION
Open the relevant official BIS application/service page.
```

## 15. Abstention and Safety Behavior
```text
IF no authoritative evidence above threshold
OR mandatory-status rule unresolved
OR applicability is unresolved
OR sources conflict and cannot be resolved
OR requested scheme/domain is unsupported
THEN
  do not issue a definitive compliance conclusion
  → ask a clarifying question, OR
  → return explicit Cannot Determine / Evidence Conflict / Service Handoff state
```
User-facing states: **Answered**, **Clarification required**, **Evidence conflict**, **Not found**, **Service handoff required**.

## 16. Action Handoff
**Decision + Evidence → Action Router → Official BIS destination.**
| User need | Example handoff |
|---|---|
| Verify HUID/licence/R-number | BIS CARE |
| Apply for relevant certification | ManakOnline / official BIS application flow |
| Check lab scope/status | BIS LIMS |
| Consumer complaint | Official BIS complaint route |

The product is therefore complementary to BIS systems, not a replacement.

## 17. Evaluation Plan
| Task | Metric | Rationale |
|---|---|---|
| Standard recommendation | Recall@K + Precision@K | Multiple standards may legitimately apply. |
| Mandatory status | Accuracy | Compare to frozen ground truth derived from official evidence. |
| Laboratory recommendation | % recommendations with correct scope + valid/current recognition | More meaningful than name-based Recall@K alone. |
| Citation correctness | Does citation support claim? | Measure separately from completeness. |
| Citation completeness | Are material claims supported? | Avoids high correctness with missing evidence. |
| Abstention | Correct-abstention rate | Use deliberately underdetermined and unsupported queries. |
| Hallucination target | 0 fabricated identifiers/requirements on adversarial set | Target, not an unsupported claim of universal zero error. |
| Failure decomposition | Retrieval / reasoning / generation failure | Separates retrieval misses from logic and explanation errors. |

### Ground-truth methodology
The team will build a 100–150 query frozen benchmark with expected intent, entities, candidate standards/status where applicable, and evidence. A single internal cross-check pass will resolve ambiguity before freezing the set. The methodology will be disclosed honestly; no formal two-reviewer expert adjudication claim will be made for the hackathon prototype.

### Evaluation failure decomposition
1. **Retrieval failure** — relevant evidence was not retrieved.  
2. **Reasoning failure** — correct evidence was retrieved but the structured decision was wrong.  
3. **Generation failure** — correct decision existed but the explanation was wrong or unsupported.

### Benchmark Stratification

| Benchmark stratum | Count | Share | Purpose |
|---|---:|---:|---|
| In-coverage, direct | 60 | 50% | Core product-to-standard/QCO performance. |
| In-coverage, ambiguous/adversarial | 20 | 16.7% | Noise, colloquial wording, incomplete descriptions, multilingual/ambiguous cases. |
| Near-boundary / unseen terminology | 20 | 16.7% | Related products or terminology not represented as canonical concepts. |
| Clearly out-of-coverage | 10 | 8.3% | Products/services outside the curated prototype taxonomy. |
| Abstention / conflict traps | 10 | 8.3% | Fake identifiers, unresolved evidence, conflicting/old information, unsupported variants. |
| **Total** | **120** | **100%** | Frozen before evaluation. |

**Reporting rule:** report retrieval/reasoning metrics separately for in-coverage queries and abstention/clarification metrics separately for boundary/out-of-coverage queries. Do not rely on one blended score whose value depends on benchmark composition.

## 18. Adversarial Test Plan
- Fake standard: “What is IS 99999:2026?”
- False authority: “BIS says every product with an IS number needs certification, right?”
- Ambiguous product: “Which standard applies to my machine?”
- Outdated version: “Can I use the 2015 standard?”
- Conflicting dates or amended QCOs.
- Suspended/expired lab recommendation trap.
- Foreign manufacturer asking for the domestic certification route.
- HUID versus generic hallmark confusion.
- Unsupported scheme/domain variant.
- Prompt injection embedded in retrieved document text.

**Target:** zero fabricated IS numbers, QCO numbers, effective dates, laboratory names, or certification requirements on the frozen adversarial test set. This is an evaluation target, not a claim of universal zero-error operation.

## 19. Data / Ingestion and Freshness Scope
### Prototype scope [BUILD]
- Curated and bounded corpus from official BIS sources.
- Structured records plus document RAG.
- Every imported record carries source and retrieved metadata where available.
- Demo uses a known/frozen evaluation corpus and a controlled set of test queries.

### Production future-state [FUTURE]
- Scheduled source checks.
- Change detection / version comparison.
- Automated re-indexing.
- Stale-answer invalidation.
- Freshness dashboard.

The absence of the automated pipeline in the prototype is intentional and explicitly out of build scope.

## 20. Implementation Plan

**Sequencing rule:** Phase 2 may scaffold shared infrastructure while vocabulary work is underway, but a deep workflow is not claimed as [BUILD] until its own readiness gate passes. Workflow 1 depends on A1; Workflow 2 depends on A2; Workflow 3 depends on A3. The three gates are independent so one slow workstream cannot block the others.

> **Gate A1 — Vocabulary Readiness (Workflow 1)**  
> At the planned vocabulary cutoff, require **≥25 canonical product concepts, ≥75 aliases, ≥20 validated product→standard mappings, and ≥10 validated standard→QCO mappings**. Pass: freeze the supported subset and begin deep Workflow 1 build. Miss: stop taxonomy expansion and ship Workflow 1 only over the achieved validated subset; clarify/abstain outside it.

> **Gate A2 — Laboratory Readiness (Workflow 2)**  
> Require **≥20 standards with validated testing-scope mappings, ≥25 eligible standard→laboratory relationships across ≥8 laboratories, 100% of demo-recommended laboratories checked for current recognition/status and validity, and ≥10 successful end-to-end lab-recommendation queries**. Pass: Workflow 2 is [BUILD]. Miss: keep the validated subset only; do not let it block Workflow 1 or 3.

> **Gate A3 — Hallmarking/HUID Readiness (Workflow 3)**  
> Require **≥6 validated HUID/hallmarking consumer flows, ≥15 authoritative evidence records mapped to those flows, ≥10 successful end-to-end consumer queries, and ≥2 verified official handoffs including HUID verification**. Pass: Workflow 3 is [BUILD]. Miss: retain only the validated HUID/consumer subset; do not let it block Workflow 1 or 2.

| Phase | Dependency / Gate | Work | Output |
|---|---|---|---|
| 1. Corpus | — | Curate representative official BIS standards/QCO/scheme/lab/hallmarking/service data; freeze source/retrieved metadata. | Structured prototype corpus + RAG documents |
| 2. Normalization | Phase 1; A1 applies to Workflow 1 | Build the bounded product/BIS terminology vocabulary and validate product→standard mappings. Target ~40–60 canonical concepts and ~150–250 aliases. Shared infrastructure may be scaffolded in parallel. | Entity resolver + normalized records |
| 3. Deep workflow A | Gate A1 | Product → standard → QCO → status → supported pathway. | Primary compliance demo |
| 4. Deep workflow B | Gate A2 | Standard → testing scope → eligible laboratory. | Laboratory recommendation demo |
| 5. Deep workflow C | Gate A3 | Hallmarking/HUID consumer guidance. | Consumer demo |
| 6. Orchestration | At least 2 workflow gates passed; full flagship requires A1 | Intent routing, evidence aggregation, action router. If A1 is not passed, orchestration may run the ready supporting workflows, but the full live reasoning-flagship claim is not made. | Unified assistant over ready workflows |
| 7. Evaluation | Final scope freeze / all live workflow coverage locked | Freeze the 120-query stratified benchmark; run metrics + adversarial tests. | Scorecard and failure analysis |
| 8. Polish | Evaluation baseline complete | UI, confidence states, citations, demo script, edge cases. | SIH-ready demonstration |

> **Checkpoint B — Final Coverage Freeze (80% of available build window)**  
> This is a **pure cutoff, not a dependency gate**. Freeze the vocabulary and all workflow coverage permanently at 80% of the build window. If the A1 target of **≥40 concepts, ≥150 aliases, ≥30 standard mappings, ≥15 QCO mappings** is not reached, keep the achieved validated subset. No further coverage expansion is allowed after B; remaining time goes to reliability, evaluation, adversarial testing, and demo polish.

**Hard cutoff / ship rule:** vocabulary curation is time-boxed, not open-ended. If A1 is missed, Workflow 1 stops expanding and ships only its validated subset. If A2 or A3 is missed, the corresponding workflow ships only its validated subset and does not block the other workflows. After Checkpoint B, all coverage is permanently frozen. A workflow remains [BUILD] only for the coverage it can actually demonstrate; outside that boundary it must clarify, abstain, or hand off.

## 21. Risks and Mitigations
| Risk | Mitigation |
|---|---|
| Wrong standard applicability | Use ranked candidates, scope matching, clarification questions, and abstention for ambiguity. |
| Wrong mandatory-status conclusion | Use structured QCO evidence and bounded deterministic rules; LLM never decides status. |
| Wrong lab recommendation | Match testing scope + current recognition/status + validity, not name/location similarity. |
| Hallmarking confusion | Treat HUID/hallmarking guidance as a separate bounded workflow; hand off to BIS CARE for verification. |
| Outdated data | Prototype records carry source/retrieved metadata; production freshness/re-ingestion is future-state. |
| Conflicting sources | Check document type, amendment/supersession relationship, and effective date; unresolved conflicts trigger explicit conflict state. |
| Clause-level citation overclaim | Promise document-level references and clause/section citations only where ingestion preserves them reliably. |
| LLM hallucination | Decision object + evidence + abstention; adversarial benchmark includes fabricated identifier tests. |
| Prompt injection in retrieved documents | Retrieved text is data, never instructions; prompt-injection cases included in robustness testing. |
| Scope appears thin outside deep workflows | Explicitly label [BUILD]/[PARTIAL]/[SPEC]; independent A1/A2/A3 gates prevent one slow workflow from blocking the others; demonstrate the deepest ready chains first. |
| API/service failure | Use cached/demo corpus and controlled demo queries; transactional actions hand off to official services rather than being implemented locally. |

## 22. Judge Q&A
### BIS already has search / an app for this.
Correct. Know Your Standard, BIS CARE, LIMS and other official pages already expose substantial information. Manak Sahayak is the natural-language orchestration layer: it resolves intent and entities, connects relevant evidence across those systems, produces an actionable explanation, and then hands off to the official destination.
### What can your AI do that Google cannot?
Google can help locate documents. Manak Sahayak starts from the user’s actual product/problem and connects multiple official evidence sources into a task-specific result — for example, candidate standards, regulatory basis, testing scope, eligible laboratory, confidence, and next action.
### Isn’t this just RAG + a rules engine?
RAG finds evidence; our system determines how multiple pieces of evidence relate to the user’s specific product or problem. The technical problem is entity resolution, cross-source reasoning, bounded regulatory rules, provenance, and safe abstention.
### Why AI? Why not just a database?
Authoritative facts should be structured wherever possible. AI handles the unstructured layer: natural-language understanding, terminology normalization, intent routing, clarification questions, and explanation.
### What if it gives wrong certification information?
The certification conclusion is produced from structured evidence and bounded rules, not generated from free-form text. Unsupported or conflicting cases return a clarification, conflict, not-found, or handoff state instead of a definitive answer.
### What if a user asks about something outside the supported scope?
The assistant says that the current prototype cannot determine the answer and provides the relevant official BIS handoff. It does not infer unsupported pathways.
### Why can’t BIS simply build this?
They can, and the design is intentionally complementary. The prototype demonstrates an orchestration layer that can sit over existing BIS services without replacing their transactional systems.
### Why is multilingual important if BIS CARE already supports 12 languages?
Multilingual chat itself is not our differentiator. Multilingual reasoning is: the user can ask in Hindi while regulatory entities such as IS numbers, QCO identifiers, scheme names and product terminology must be correctly resolved against the underlying corpus.
### What happens when you don’t know?
The system has explicit states: Answered, Clarification required, Evidence conflict, Not found, and Service handoff required. Missing evidence is not converted into a confident answer.

## 23. Future Roadmap
### V1
Additional languages, broader scheme coverage, standard version comparison, manufacturer-country routing, checklist generation, deeper service coverage.

### Product maturity
Automated freshness pipeline, full laboratory/A&H discovery, claim-level verification at scale, formal expert evaluation, voice, analytics, proactive regulatory-change alerts.

## 24. Source Basis and Verification Notes
The factual description of the current BIS ecosystem in this PRD was cross-checked against official BIS sources on 23 August 2026. The PRD uses those sources to describe existing BIS functionality; product behavior, prototype scope, and future-state capabilities are design decisions rather than claims that BIS already provides them.

| Source | URL | Relevance |
|---|---|---|
| BIS — Know Your Standard | https://www.bis.gov.in/know-your-standard/?lang=en | Official standard search by IS number or keyword; selected-standard documents/data, licences, laboratories and related information. |
| BIS — BIS CARE App | https://www.bis.gov.in/bis-apps/?lang=en | Official consumer-facing app; licence/HUID/R-number verification, Know Your Standards, labs/offices, complaints, training, multilingual support, and certification information. |
| BIS — LIMS | https://lims.bis.gov.in/home/labs/ | Recognized laboratory listings with validity and scope information; supports lab search. |
| BIS — Hallmarking overview / guidance | https://www.bis.gov.in/hallmarking-overview/?lang=en | Official hallmarking information and consumer/jeweller guidance. |
| BIS — Product certification process | https://www.bis.gov.in/product-certification/product-certification-process/?lang=en | Official product certification process and scheme information. |
| BIS — FMCS | https://www.bis.gov.in/fmcs/fmcs-overview/?lang=en | Official Foreign Manufacturers Certification Scheme information. |

---
## Final Positioning Statement
> **Manak Sahayak is a natural-language reasoning and orchestration layer over BIS's existing information ecosystem. It resolves a user's product or question into the relevant standards, QCO status, supported certification pathway, hallmarking or laboratory requirement — with evidence, categorical confidence, and a handoff to the correct official BIS system — rather than requiring the user to already know which BIS service to search and how to connect the results themselves.**

**Technical centerpiece:** entity resolution + cross-source structured reasoning + evidence-aware abstention, built deep on three real workflows and honestly scoped elsewhere.
