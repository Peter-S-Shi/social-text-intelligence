# Development Log

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
