# Architecture

## Milestone 8 boundary

Milestone 8 adds a descriptive insight layer to successful Milestone 6 batch
outcomes and the separate Milestone 7 review state. It validates trusted
metadata grouping, preserves AI/human/agreement perspectives, calculates exact
metric denominators and sample warnings, stores manual context notes separately,
selects examples by explicit rules, and shapes explicit exports. It intentionally
adds no model rerun, inferred identity, LLM narrative, ranking, persistence,
platform connector, French capability, moderation workflow, or hosted deployment.

The current package contains:

- `foundation.py`: immutable project status and capability metadata;
- `cli.py`: diagnostics and single-text model commands;
- `contracts/`: normalized input, result, provenance, and error contracts;
- `providers/`: stable protocols, deterministic test implementations, a pinned
  Cardiff NLP sentiment adapter, and a pinned Sam Lowe emotion adapter;
- `services/`: provider-neutral orchestration, thread-safe lazy reuse, CSV batch
  processing, reusable human-review rules, and reusable insight grouping,
  metric, context-note, example-selection, and export rules;
- `interface/`: local Flask routes, templates, and static presentation only.

Dependency direction is `services -> providers -> contracts`. Contracts do not
depend on providers, model libraries, persistence, or UI code.

The optional Transformers/PyTorch runtime is imported lazily inside the concrete
providers. Installing the core or running fast tests therefore does not require
a model library or weight download. `SentimentAnalysisService` remains
sentiment-only. `AnalysisService` produces one `AnalysisReport` by invoking the
sentiment and emotion providers for the same normalized record without logging
or persistence. `LazyAnalysisService` owns one lazily built `AnalysisService` per
application process. Flask routes create normalized records and render results;
they do not load models, map labels, or write data.

Batch business rules remain in `services/batch.py`, independent of Flask. The
interface keeps each active upload in a random-token, capacity-limited,
time-limited in-memory workspace. Preview replaces raw upload bytes with typed
rows; analysis adds normalized outcomes. Clearing or expiry removes the
workspace. No temporary file or database is created.

`services/review.py` owns the human-review contracts and all label validation,
record-status semantics, navigation selection, agreement calculations, summary
denominators, and reviewed export shaping. `HumanReview` never contains or
replaces an `AnalysisReport`; it references the record identity and stores only
human fields. Each update returns a new `ReviewState`, while the original frozen
batch result remains unchanged. Flask parses forms and replaces the review state
inside the existing random-token workspace.

`services/insights.py` owns the trusted grouping allowlist, perspective/metric
compatibility, filters, aggregation and denominator calculations, sample-size
policy, context-note validation, deterministic example selection, and insight
export shaping. It reads `BatchResult` and `ReviewState` without modifying them.
`InsightState` contains only separate context notes and is replaced immutably in
the same bounded workspace. Templates render already-computed values; they do
not define statistical rules or rerun providers.

## Intended layers

Future milestones should preserve these boundaries:

1. input adapters;
2. normalization and chunking;
3. typed domain contracts;
4. model providers;
5. analysis services;
6. human-review workflows;
7. local persistence;
8. reporting and analytics;
9. user interface.

Dependencies should point inward toward typed domain contracts. UI code must not
load models or implement persistence rules. Platform-specific inputs must remain
optional adapters.

## Testing strategy

Fast tests run without network access or model downloads by injecting a small
runtime stub. The opt-in test under `tests/integration/` loads the immutable real
model revisions only when `STI_RUN_MODEL_TESTS=1`. All fixtures are synthetic.
Private user text must never become a test fixture.
