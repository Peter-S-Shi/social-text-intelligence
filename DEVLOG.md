# Development Log

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
