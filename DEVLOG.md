# Development Log

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
