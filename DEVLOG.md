# Development Log

## Product Hardening Batch A3 — Global HTTP request-body boundary

Reconciled Phase 0 PH-004 as permanent FCR-047. FCR-025 covers privacy and
local-state consistency, while FCR-029 covers existing error and recovery
states; neither defines a framework-level body limit before Flask parses form
or multipart input.

The local Flask app now uses a configurable 3 MiB `MAX_CONTENT_LENGTH` request
ceiling. This is deliberately 1 MiB (50 percent) above the existing 2 MiB CSV
payload limit so multipart headers and form encoding have clear capacity. The
two limits remain independent, and configuration rejects a request ceiling
that is not greater than the CSV payload limit.

A lightweight `before_request` check rejects declared oversized bodies before
any route or temporary-state operation, including POST routes that otherwise do
not parse their bodies. Flask's request-reading limit provides the same boundary
during form/multipart parsing. One minimal 413 handler returns only fixed copy
and the configured byte limit; it never reads or echoes submitted content.
Existing `Cache-Control: no-store` and `Pragma: no-cache` response handling
continues to cover 413 responses.

Targeted regressions passed 12/12: seven boundary cases across Direct, Batch
multipart, an unparsed Batch action, Review, Insights notes, and Triage
decisions, plus five unchanged normal-flow checks. They prove no input echo, no
traceback/path disclosure, no state creation or mutation, and the independence
of the CSV byte limit. The full suite passed 148 with 2 opt-in real
model tests skipped; Ruff, strict MyPy for 69 files, compileall, and pip check
passed. Behavioral candidate:
`def0577feb3c43d4e9e81577003c43da821b6ba2`.

Batch A2 was merged through PR #19 at main SHA
`1c9764ba7bcd45b07a07a93077b86070e358a0ab`; this is the synchronized A3
baseline. Feature Freeze remains PASS. PH-005 and PH-007 are not started.

## Product Hardening Batch A2 — Input truthfulness / no silent truncation

Reconciled Phase 0 PH-003 as permanent FCR-046. Existing FCR-003, FCR-006,
and FCR-008 cover input recovery, model-limit communication, and Batch partial
failure separately; none supplied the required cross-provider complete-input
success invariant.

Both pinned Transformers runtimes now encode with special tokens enabled and
`truncation=False`, then compare the real encoded sequence length with an
audited 512-token provider budget before inference. SamLowe declares 512 in its
tokenizer metadata. The pinned Cardiff tokenizer exposes the Hugging Face
unknown-limit sentinel, so the reviewed 512-token contract is explicit and
checked against the loaded model's position capacity. Incompatible finite
metadata fails closed.

Combined analysis preflights both required providers before either inference.
Direct and CLI requests return `model_input_too_long` with an explicit statement
that no truncation or partial analysis occurred. Batch isolates the failure to
the affected row, continues valid rows, and exports no model labels, scores,
identities, or revisions for the failed row. The 20,000-character application
safety ceiling remains separate. No chunking, aggregation, summarization,
model/revision/threshold change, persistence, or successful-result truncation
field was added.

Targeted complete-input regressions passed 9/9. The full suite passed 141 with
2 opt-in integration tests skipped; Ruff, strict MyPy for 69 files, compileall,
and pip check passed. A separate cached, offline run of both real-model smoke
tests passed 2/2. The user-approved code review and PR #19 final-head CI passed,
so FCR-046 is closed as `VERIFIED` on the exact behavioral candidate below.
The exact behavioral candidate is
`31b5e6cf7fc6d551bb72680900976595008d9d7c`; the following documentation
commit does not change that tested behavior.

Batch A1 was merged through PR #18 at main SHA
`1b36fe8c024823c1f4829621a7bcc733b2915c93`; this is the synchronized A2
baseline. FCR-045 remains `VERIFIED`.

## Product Hardening Batch A1 — Ephemeral Batch state integrity

Reconciled Phase 0 findings PH-001 and PH-002 as one permanent product finding,
FCR-045. FCR-036 remains the separate, already-verified confirmation contract
for user-initiated clear; FCR-045 addresses the shared Batch-store root cause:
capacity eviction and missing active-analysis write-back protection.

Batch capacity now blocks new uploads with an explicit conflict instead of
deleting existing work. Synchronous analysis acquires an exclusive in-memory
lease, remains protected from normal TTL purge and clear while active, and may
commit only through its current lease. A rejected write-back is an explicit
409 and never follows the success path. Explicit clear still releases capacity,
inactive TTL expiry remains unchanged, and no database, persistence, recovery
worker, background task, model, threshold, or privacy contract was added.

Targeted regressions cover `capacity+1`, inactive expiry, active analysis across
TTL, duplicate/stale write-back, clear conflict and recovery, and preservation
of existing Batch results, Review, Insights, and linked Triage workspaces when
a new upload is blocked.

PR #18 review found one narrow error-render regression: `/batch/upload` without
a file did not pass the configured concurrent workspace limit to `batch.html`.
Correction SHA `729318c6c253ea8eee8351e766bbcfe7a335c297` restores that context
and adds a configured-limit route regression. Targeted Batch routes passed 6/6,
the full suite passed 132 with 2 opt-in real-model tests skipped, all local
quality checks passed, and PR #18 remote CI passed on Python 3.11/3.12/3.13.
FCR-045 is therefore closed as `VERIFIED`; PH-003 remains outside this batch.

## Feature Freeze closure

Recorded the user's explicit Feature Freeze PASS for tested behavioral SHA
`16acb0f5931b022b57f0c5cdbe4501973aa3ad11` after the candidate-specific
final-head smoke test passed. FCR-044 is manually verified, FCR-002 navigation
verification is re-closed, and V-01 is satisfied by the exact SHA. FCR-042 and
FCR-043 remain non-blocking Product Hardening backlog.

This closure changes governance documentation only. It does not modify product
behavior, models, revisions, thresholds, privacy contracts, workflows, or the
tested behavioral candidate. Release readiness remains No; the next lifecycle
phase is Product Hardening.

## Review ergonomics — Windows one-click launcher

Added `start_social_text_intelligence.bat` at the repository root after explicit
user approval. The launcher resolves the project `.venv` with relative paths,
starts the existing loopback-only web app in offline mode, opens the browser,
and provides setup and shutdown guidance. It installs and downloads nothing and
does not change application, model, privacy, or persistence behavior.

## Feature Complete Review — FCR-044 return navigation

Reclassified FCR-044 as a pre-freeze blocker after candidate-specific manual
review showed that four internal Support Triage views lacked a discoverable
return to the main application and caused material operating difficulty. Added
an explicit `Social Text Intelligence home` link to every non-root workflow
view, including deep Triage and Moderation pages, while preserving each
workflow's own subnavigation and all temporary state.

Reopened FCR-002 navigation verification and added route regressions covering
the four Triage internal views plus Moderation session/review pages. No workflow,
model, data, privacy, persistence, or decision semantics changed.

## Feature Complete Review — pre-freeze blocker corrections

Classified the completed manual review into product findings, QA governance,
and release ergonomics. Recorded FCR-034 through FCR-044 without treating every
questionnaire suggestion as a product FCR. Established a tracked `manual-qa/`
home for the bilingual questionnaire, synthetic samples, and guidance, while
repository ignore rules keep raw results, screenshots, exports, and machine
paths out of Git.

Clarified emotion neutral threshold-fallback copy, added Batch filter anchoring
and destructive-clear confirmation, surfaced Human Review completion and
Context Note UTC timestamps, exposed reliable/unassigned Insight failure
counts, made Triage no-mock state explicit, and restored the linked
Batch-to-Triage entry. These changes preserve models, thresholds, labels,
privacy defaults, denominators, and process-memory boundaries. Feature Freeze
remains pending explicit approval after candidate-specific manual retest.

## Feature Complete Review — local model-cache hardening

Hardened the pinned Cardiff sentiment runtime so Transformers must load the
audited `pytorch_model.bin` artifact and cannot silently create a separate
Safetensors conversion-revision snapshot. Added a regression test for the
immutable revision, offline option, remote-code boundary, restricted weight
loading, and explicit artifact choice.

Repaired the machine-local Hugging Face cache after Windows Developer Mode was
enabled: the duplicate GoEmotions snapshot weight is now a symbolic link to its
content-addressed blob, and the unused Cardiff auto-conversion revision was
removed after real offline inference passed for both providers. Cache repair is
local-only and does not change a model, approved revision, label, score, product
contract, or tracked model artifact.

## Lifecycle alignment after Milestone 10

Created `ROADMAP.md` as the canonical mutable roadmap and
`PROJECT_STATUS.md` as the canonical current-state record. Added the bilingual
Feature Complete Manual Audit and the living manual-QA artifact, then aligned
the README, Charter, and development guidance around the post-M10 lifecycle.

The current phase is Feature Complete Review. Feature Freeze, Product
Hardening, full regression and manual acceptance, and Release Candidate
approval have not started or passed. Former M11–M12 remain deferred
next-version candidates; former M13 is lifecycle evaluation, hardening,
acceptance, portfolio, and delivery work rather than another future feature.

## Milestone 10 — Local Support Triage workbench

Added a separate three-area Support Triage workflow over a versioned,
project-authored synthetic routing guide and 22 stable synthetic tickets.
Successfully parsed batch records are eligible through explicit snapshots even
when NLP inference failed; optional sentiment, emotion, human review, context
notes, and trusted metadata remain supporting context and never determine
routing automatically.

Added typed intents, categories, urgency, recommended queues, escalation
reasons, recommended actions, draft/finalized states, guide provenance,
deterministic mock provenance, structural validation, and non-blocking warning
contracts. Drafts may be incomplete but legal. Finalization is atomic and
freezes an immutable first decision; explicit revisions update a separate
current final decision.

Added Independent and deterministic mock-assisted simulation modes without a
real classifier or LLM. Human forms are never prefilled. First/final field-level
agreement and overrides remain descriptive and are never labeled accuracy,
quality, causal impact, or operator performance.

Added sample-aware summaries, overlapping follow-up reasons, filters, sorting,
and auditable formula-safe CSV export. Workspace-derived source text, NLP
signals, human review, context notes, and trusted metadata are blank by default
and require separate explicit opt-ins. Triage workspaces are process-memory
only, expire after inactivity, and block limits without silent eviction.

Planned feature milestones are now complete, but the project is not
feature-frozen or release-ready. Former Milestones 11–12 are deferred
next-version candidates. Former Milestone 13 is lifecycle work covering
evaluation, hardening, acceptance, portfolio, and delivery.

## Milestone 9 — Moderation training workflow

Added a versioned, project-authored synthetic moderation policy and a 20-case
synthetic training library with stable IDs, policy-clause provenance, complete
reference decisions, acceptable alternatives, sensitive-content markers, and
an explicitly labeled fixture mock provider. The mock provider executes no
model and is never presented as expert judgment or accuracy ground truth.

Added typed moderation contracts and separate structural validation versus
non-blocking policy guidance. Structural errors reject incomplete or conflicting
decisions. Guidance warnings preserve unusual but contextually possible
combinations without rewriting or blocking the user's judgment, and remain in
feedback, comparisons, and export. References distinguish `built_in` from
`self_authored`; the reserved `user_authored` provenance is not exposed as a
current single-user authoring choice.

Added explicit successful-record snapshot preparation, frozen policy/reference
sessions, independent and synthetic-mock-assisted modes, immediate or
end-of-session feedback, immutable first decisions, explicit final revisions,
cancel/restart history, field-level comparison, educational flags, sample-aware
raw summaries, and auditable formula-safe CSV export with privacy-default
exclusions.

Added a three-area Prepare, Train, and Review interface plus configurable
process-memory limits of 100 prepared cases, 50 cases per session, and 20
retained attempts. Limits block new objects without silently deleting existing
work. This milestone adds no live moderation model, automatic enforcement,
support triage, LLM, persistence, platform connector, account, French support,
or new dependency.

## Milestone 8 — Insights and community context

Added reusable trusted-group validation, separate AI/human/agreement
perspectives, exact metric-specific denominators, review-coverage measures, and
per-group sample-size policy. AI activation remains threshold-based and
multi-label; definitive human and disagreement metrics exclude partial and
uncertain dimensions without silently changing the denominator.

Added Group Explorer, two-to-four-group Distribution Comparison, AI vs Human,
Representative Cases, Phrase and Context Notes, and explicit Insight Export to
the existing local Flask workspace. Examples are selected by declared
deterministic rules. Context notes are user-authored, validated, and stored
separately from immutable AI results and human reviews.

Insight summaries retain model and review provenance, disclosures, filters, raw
counts, denominators, and sample warnings. Optional record-level and native-score
export remains off by default, and formula-like user-controlled cells are
escaped. A narrow conformance patch made exports self-auditing with UTC export
and context-note timestamps, metric definitions, configured sample thresholds,
complete input/analysis/review counts, and explicit successful, failed, and
unassigned failed-row group context. Failed rows are grouped only from reliably
validated supported metadata and never by inference. This milestone adds no
model, dependency, LLM narrative, inferred identity, ranking, causality,
automation, persistence, account, cloud service, platform connector, French
support, or moderation workflow.

## Milestone 7 — Human-in-the-loop review

Added a focused review queue for successful batch outcomes. Sentiment and
multi-label emotion use separate accept, correct, and uncertain judgments;
partial work remains unreviewed until both dimensions are decided. Corrected
emotion labels enforce compact-taxonomy membership, uniqueness, dominant versus
secondary separation, stable ordering, and neutral exclusivity. Human fields are
replaced immutably without rewriting the original AI report or provenance.

Added review-state and AI-label filters, safe queue navigation, per-record Accept
Both, optional notes, honest model-human agreement summaries, sentiment confusion,
emotion set comparisons, and bounded confidence-band descriptions. Agreement
denominators exclude whole-record partial reviews, failures, and the uncertain
dimension. No result is described as model accuracy or calibrated confidence.

Added explicit reviewed CSV export with separate human fields, agreement values,
UTC timestamps, failures, AI results, model revisions, and optional native scores.
Spreadsheet formula protection covers review notes and existing user-controlled
cells. Reviews share the bounded, expiring in-memory batch workspace and add no
database, autosave, re-import, training, accounts, cloud service, or Milestone 8
analytics.

## Milestone 6 — Batch input and export

Added an explicit CSV upload, column-selection, preview, and validation workflow.
Supported normalized metadata is trusted only by name; unknown columns are
reported and ignored. Missing IDs receive deterministic row identities, while
duplicate supplied IDs and invalid rows remain visible typed outcomes.

Added resilient sequential batch analysis using the same lazily reused providers,
one outcome per input row, filters, semantically distinct aggregate views, and
explicit normalized CSV export with optional native emotion scores. CSV cells
that could trigger spreadsheet formulas are safely escaped.

Uploads and results use a bounded, expiring in-memory workspace and no durable
storage. This milestone adds no database, automatic export, history, accounts,
French model support, platform connector, or hosted deployment.

## Milestone 5 — Local analysis interface

Added an original local Flask interface for direct English text analysis. The
page displays normalized sentiment and emotion results, optional native scores,
threshold and provenance details, operating mode, first-load guidance, and
plain-language limitations.

Added a thread-safe lazy analysis-service container so both model providers are
constructed once and reused across requests. Expected validation, language,
cache, dependency, and provider failures become safe user-facing messages. The
server binds to loopback and does not log or persist submitted text.

This milestone adds no batch input, history, persistence, accounts, French,
platform connectors, hosted deployment, or separate frontend application.

## Milestone 4 — Licensed fine-grained emotion analysis

Audited English social-text emotion models for license clarity, provenance,
base model, immutable revision, native labels, multi-label support, neutral
semantics, loading format, and technical fit. Approved the MIT-licensed Sam Lowe
GoEmotions model and its Safetensors artifact; documented rejected candidates.

Added local multi-label inference, preservation of all 28 native probabilities,
conservative compact taxonomy mapping, explicit inclusive threshold semantics,
dominant and ordered secondary emotions, neutral fallback, typed validation, and
a single-text combined sentiment/emotion report. Added deterministic tests and
an opt-in real-model combined smoke test.

This milestone adds no UI, batch input, persistence, French capability, platform
connector, remote inference, real user text, dataset, or model weights.

## Milestone 3 — Licensed local sentiment analysis

Audited locally executable sentiment models for license clarity, provenance,
native-label compatibility, loading safety, language, and technical fit. Approved
the Cardiff NLP Twitter-roBERTa sentiment model at an immutable revision and
documented rejected candidates.

Added lazy local inference, model-specific social-text preprocessing, one-to-one
negative/neutral/positive mapping, normalized native and application scores,
single-text service and CLI workflows, explicit unsupported-language and invalid
output handling, deterministic provider tests, and an opt-in real-model smoke
test. Updated licensing, setup, architecture, limitations, and privacy guidance.

This milestone does not add emotion inference, batch input, persistence, a user
interface, remote inference, telemetry, real user text, or model weights.

## Milestone 2 — Text analysis core contracts

Added the model-independent analysis core:

- normalized, immutable text records with explicit metadata validation;
- compact sentiment and emotion taxonomies from the Project Charter;
- separate normalized and model-native score contracts;
- provider identity, model revision, supported-language, and native-label metadata;
- stable sentiment and emotion provider protocols;
- deterministic mock providers for fast, offline tests;
- provider-neutral analysis orchestration and typed error contracts.

The mock providers do not interpret text and are not real NLP models. Milestone 2
adds no model weights, runtime dependency, persistence, UI, network access, or
user data.

## Milestone 1 — Independent local project foundation

Established the project's independent, privacy-first development baseline:

- adopted the Project Charter as the stable product reference;
- added safe Git exclusions and cross-platform text conventions;
- created a minimal dependency-free Python package and diagnostic command;
- added deterministic unit tests and continuous integration;
- documented architecture, privacy, security, development, and model governance;
- clarified that source-code licensing does not relicense models or datasets.

No NLP model, text analysis contract, user interface, persistence layer, user
data, or platform adapter is included in this milestone.
