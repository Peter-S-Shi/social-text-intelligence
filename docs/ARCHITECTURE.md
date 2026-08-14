# Architecture

## Milestone 10 boundary

Milestone 9 adds an educational moderation training workflow over a versioned
synthetic policy and case library. It may explicitly snapshot successful
Milestone 6 records together with separate M3–M8 signals, review state, and
context notes. It freezes policy/reference provenance per session, retains
immutable first decisions and explicit final revisions, separates structural
validation from non-blocking policy guidance, and shapes auditable exports. It
intentionally adds no live moderation model, enforcement action, support triage,
database, LLM narrative, platform connector, French capability, or hosted
deployment.

Milestone 10 adds a separate Support Triage domain over a versioned synthetic
routing guide and ticket library. It snapshots explicitly selected parsed batch
records without requiring NLP success, keeps optional M3–M8 context
non-authoritative, and owns draft/finalize/revision state, deterministic mock
visibility, comparisons, summaries, and privacy-aware export. It adds no CRM,
response generation, real classifier, automatic routing, persistence, or
external operation.

The current package contains:

- `foundation.py`: immutable project status and capability metadata;
- `cli.py`: diagnostics and single-text model commands;
- `contracts/`: normalized input, result, provenance, and error contracts;
- `providers/`: stable protocols, deterministic test implementations, a pinned
  Cardiff NLP sentiment adapter, and a pinned Sam Lowe emotion adapter;
- `services/`: provider-neutral orchestration, thread-safe lazy reuse, CSV batch
  processing, reusable human-review rules, and reusable insight grouping,
  metric, context-note, example-selection, moderation case/session/comparison,
  and export rules;
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

Both pinned transformer adapters share a complete-input gate. Their audited
encoded-input budget is 512 tokens, including tokenizer-added special tokens.
The runtime encodes with `truncation=False`, validates the resulting sequence
length, and only then invokes the model. The SamLowe tokenizer declares 512
directly. The pinned Cardiff tokenizer exposes Hugging Face's unknown-limit
sentinel, so its reviewed 512-token provider contract is explicit and checked
against the loaded model's position capacity. A finite tokenizer declaration
that disagrees with the audited contract fails model initialization rather than
being guessed around.

`AnalysisService` preflights both required providers before either inference.
Consequently, a successful `AnalysisReport` means the complete submitted text
was consumed by both required models (after Cardiff's documented username/URL
normalization); if either provider is over budget, no combined report is
produced. The current version deliberately has no chunking, aggregation,
summarization, or long-form workflow.

Batch business rules remain in `services/batch.py`, independent of Flask. The
interface keeps each active upload in a random-token, capacity-blocking,
time-limited in-memory workspace. Preview replaces raw upload bytes with typed
rows; analysis adds normalized outcomes. Clearing or expiry removes the
workspace. No temporary file or database is created.

Reaching the Batch workspace limit blocks a new upload and never evicts older
work. Synchronous analysis holds an exclusive in-memory lease: normal TTL purge
and explicit clear cannot remove that workspace until analysis commits or
fails. Only the current lease may write the completed state, and a rejected
write-back is reported as a conflict rather than success.

The Flask application has a framework-level 3 MiB HTTP request-body boundary,
configured through `MAX_CONTENT_LENGTH`. A `before_request` content-length gate
rejects declared oversized bodies before route or state logic, including routes
that do not otherwise parse the request body; Flask enforces the same ceiling
while reading form and multipart data. A single minimal handler returns a fixed
413 response. The 2 MiB CSV payload limit remains a separate service-level rule,
leaving 1 MiB for multipart/form encoding overhead. This boundary adds no
deployment, account, persistence, CSP, Origin, or Host policy.

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

`contracts/moderation.py` owns the moderation enumerations, structural decision
invariants, non-blocking guidance warnings, policy/reference provenance, frozen
case snapshots, and attempt/session contracts. `services/moderation_resources.py`
loads and validates packaged versioned JSON resources.
`services/moderation_training.py` owns filtering, snapshot preparation, limits,
session lifecycle, comparison, sample-aware summaries, and export shaping.
`providers/moderation_mock.py` is a fixture lookup boundary only; it executes no
model and never interprets user text.

`interface/moderation_state.py` retains random-token training workspaces in
bounded, expiring process memory. Capacity and object limits block creation
rather than evicting older work. `interface/moderation_routes.py` parses forms
and replaces immutable workspace state; it does not define policy semantics or
persist content.

`contracts/triage.py` owns support triage taxonomies, legal draft structure,
finalized structural requirements, guide departures, snapshots, provenance, and
first/final state. `services/triage_resources.py` validates the packaged guide
and synthetic ticket library. `providers/triage_mock.py` is deterministic
fixture lookup only. `services/support_triage.py` owns source eligibility,
literal snapshots, lifecycle transitions, comparisons, filters, denominators,
sample safeguards, and export shaping.

`interface/triage_state.py` provides a random-token, capacity-blocking,
sliding-expiry process-memory store. `interface/triage_routes.py` parses HTTP
inputs and replaces immutable workspace values. Templates display already
validated decisions and summaries; they do not define routing semantics.

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
