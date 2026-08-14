# Social Text Intelligence

Social Text Intelligence is a privacy-conscious, local-first NLP workbench in
development. Its long-term purpose is to support sentiment, emotion, and
human-in-the-loop analysis of feedback, comments, transcripts, and other social
text with transparently licensed open-source models.

> **Current lifecycle phase: Release Candidate**
>
> Planned feature milestones 1–10 are complete, Feature Complete Review is
> completed, Feature Freeze is PASS, Product Hardening is complete, Full
> Regression and Manual Acceptance is PASS, and the Release Candidate Gate is
> PASS. An explicit Version / Delivery Decision by the repository owner is
> still required, so the current version is not release-ready.

## Principles

- Local inference is the default; user text should remain on the user's device.
- Model output is an estimate, not objective truth or psychological diagnosis.
- Every model and dataset must have a documented, compatible license.
- AI predictions and human-reviewed decisions must remain distinguishable.
- Platform integrations must be optional adapters, not core dependencies.

The stable product and engineering direction is defined in the
[Project Charter](PROJECT_CHARTER.md). Mutable planning and current execution
state are maintained separately:

- [Product Roadmap](ROADMAP.md)
- [Project Status](PROJECT_STATUS.md)
- [Feature Complete Manual Audit](docs/FEATURE_COMPLETE_MANUAL_AUDIT.md)
- [Manual Acceptance Gate Standard](docs/MANUAL_ACCEPTANCE_GATE.md)
- [Living Manual QA](manual-qa/manual_review_questionnaire.html)

## Quick start

Python 3.11 or newer is required.

```text
git clone <repository-url>
cd social-text-intelligence
python -m venv .venv
```

Activate the virtual environment using the command appropriate for your shell,
then install the package:

```text
python -m pip install --upgrade pip
python -m pip install -e .
sti about
sti contracts
```

Install the optional local sentiment runtime when you want real inference:

```text
python -m pip install -e ".[sentiment]"
sti sentiment "I am pleased with this synthetic example."
```

Install both model extras for a combined single-text report:

```text
python -m pip install -e ".[sentiment,emotion]"
sti analyze "Thank you so much for the thoughtful help!"
```

The first command invocation downloads the approved model revision from its
original Hugging Face repository into the ignored `model_cache/` directory.
Inference then runs on the local machine; input text is not sent to an inference
API. Use `--offline` after both models are cached to forbid network retrieval.
Both model commands reject an input that the pinned tokenizer/model cannot
consume in full. They never silently truncate or present partial-text inference
as a whole-text result.

Run the local interface after installing the web and model extras:

```text
python -m pip install -e ".[web,sentiment,emotion]"
sti-web
```

Open `http://127.0.0.1:5000`. Use `sti-web --offline` after both pinned model
revisions are cached. The server binds only to the local loopback interface.
Every non-root workflow view provides an explicit
`← Social Text Intelligence home` link. Deep workflow navigation remains
separate, so returning home never clears or rewrites temporary workspace state.

On Windows, after the environment and both models are installed, double-click
`start_social_text_intelligence.bat` in the project folder. It starts the same
offline loopback-only server and opens the browser automatically. Keep its
console window open while using the application; press Ctrl+C there to stop it.
The launcher uses only project-relative paths and does not install, download, or
persist anything.

The local server enforces a 3 MiB HTTP request-body ceiling before form or
multipart processing. Oversized requests receive a fixed privacy-safe 413
response and cannot create or modify temporary workflow state. This ceiling is
separate from the 2 MiB CSV payload limit and includes 1 MiB of multipart/form
encoding capacity. Advanced local runs may configure it with
`sti-web --max-request-bytes`, but it must remain greater than
`--max-batch-bytes`.

The browser interface accepts only `127.0.0.1` and `localhost` Host values
(ports are allowed) and the CLI continues to bind only `127.0.0.1`. Unsafe
browser methods require a same-origin `Origin`, or a same-origin `Referer` when
Origin is absent. Requests with neither header remain supported as explicit
local non-browser clients behind the trusted-Host boundary. Explicit external,
cross-origin, or `null` origins are rejected before route logic, model loading,
or workspace mutation. Responses use a strict self-hosted CSP, `nosniff`, a
same-origin referrer policy, anti-framing protection, and no-store caching. The
loopback HTTP product intentionally does not emit HSTS or enable CORS.

Run the dependency-free test suite:

```text
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

For the complete contributor workflow, see
[Development](docs/DEVELOPMENT.md).

## Local sentiment analysis

Milestone 3 adds a single-text English workflow through the existing normalized
contracts and provider boundary. Each result includes negative, neutral, and
positive scores, the selected label, confidence, model identity, and immutable
revision. Output is an estimate that still requires contextual human judgment.

The selected model, alternatives, license evidence, mapping, supply-chain
controls, and limitations are documented in the
[Milestone 3 Model Audit](docs/MODEL_AUDIT.md).

## Fine-grained emotion analysis

Milestone 4 adds an immutable English GoEmotions provider and connects it to the
sentiment provider through the existing `AnalysisService`. The combined report
preserves all 28 native emotion probabilities, compact scores, an inclusive
threshold, dominant emotion, ordered secondary emotions, model identities, and
revisions.

Compact neutral means no mapped non-neutral emotion reached the threshold. It is
not a psychological conclusion. Scores are independent multi-label probabilities
and do not sum to one. See the
[Milestone 4 Emotion Model Audit](docs/EMOTION_MODEL_AUDIT.md) for the full
candidate review, mapping, threshold rules, licenses, and limitations.

## Local analysis interface

Milestone 5 presents the combined analysis through a small, accessible Flask
interface. It shows all sentiment scores, compact and optional native emotion
scores, threshold semantics, immutable model identities, operating mode, and
prominent limitations. Both providers load only on first analysis and are reused
for later requests in the same process. User text is neither logged nor stored by
the application.

## Batch CSV workflow

Milestone 6 adds a separate Batch CSV mode:

1. upload a UTF-8 CSV for preview and validation;
2. select the text column if `text` is absent;
3. explicitly start local analysis;
4. inspect distinct sentiment, dominant-emotion, and multi-label activation
   aggregates;
5. filter row outcomes and explicitly export normalized CSV results.

The default limits are 2 MiB, 500 rows, and a 20,000-character application
safety ceiling per text. Separately, each pinned model enforces its audited
512-token encoded-input budget after real tokenizer encoding, including special
tokens. If either required model cannot consume a row in full, that row receives
an explicit `model_input_too_long` error; no partial inference is run, other
valid rows continue, and exports leave model scores and provenance blank for the
failed row. Required
and supported metadata fields are documented in [Contracts](docs/CONTRACTS.md).
Duplicate supplied IDs, invalid metadata, empty text, unsupported languages, and
provider failures remain row-level outcomes and do not abort the batch. Uploaded
content is held only in bounded, expiring process memory; there is no database,
automatic save, or upload history. Native emotion scores are an optional export.
Use `sti-web --help` to configure the file-byte, row-count, and per-text limits
for a local session.

## Human-in-the-loop review

Milestone 7 adds a focused queue for successfully analyzed batch rows. Sentiment
and emotion are judged independently as `accept`, `correct`, or `uncertain`.
Human labels and notes remain separate from immutable AI predictions and pinned
model provenance. A row becomes reviewed only after both dimensions have a
judgment; partially reviewed and uncertain dimensions do not enter formal
agreement denominators.

The review page supports previous, save-and-next, next-unreviewed, per-record
Accept Both, and All/Unreviewed/Reviewed/Corrected/Uncertain filters. Its summary
reports progress, sentiment confusion, exact emotion-set agreement, label
additions/removals, and a descriptive confidence-band comparison only after five
definitive reviews. It uses the term agreement rather than accuracy and makes no
confidence-calibration claim.

Reviewed CSV export preserves every original AI field, errors, provider/model
revisions, separate human fields, timestamps, and true/false/blank agreement
semantics. Native emotion scores are optional. Reviews remain in bounded,
expiring process memory until the user exports them; there is no review database,
background save, import, training, or reviewer account system.

## Insights and community context

Milestone 8 adds a local descriptive insight layer over the existing frozen
batch results and separate review state. Group Explorer and Distribution
Comparison use only trusted user-supplied `source_type`, `source_label`, `topic`,
`community`, `language`, or valid timestamp-month metadata. The application does
not infer groups from text, names, slang, locations, or model output.

AI prediction, definitive human-reviewed, and AI-human agreement perspectives
remain separate. Every metric displays raw counts, its eligible denominator,
review coverage where relevant, and a per-group sample warning. Fewer than five
eligible records suppress comparative percentage emphasis; five through nine
show a prominent small-sample warning. No view produces rankings, composite
scores, causal claims, cultural generalizations, or psychological conclusions.

Phrase and Context Notes are written manually by the user and remain separate
from AI and human labels. Representative Cases are selected by explicit rules
such as low confidence, definitive disagreement, correction, uncertainty, or
note presence, and always state why each case appears. Insight CSV export is an
explicit action. Its audit row records UTC export time, metric definition, sample
thresholds, complete input/analysis/review counts, selection, filters, model
provenance, and emotion-threshold semantics. Group summaries distinguish
successful and failed rows; failures are grouped only from independently valid
supported metadata and otherwise remain explicitly unassigned. Notes include a
UTC creation time, while supporting records and model-native scores are optional.
All insight state remains in the same bounded,
expiring process-memory workspace and is cleared with the batch.

Clearing a batch requires explicit confirmation and explains that its linked
review and insight state will also be removed. Filter submissions return to the
Results section without changing their semantics.

## Moderation training

Milestone 9 adds a separate three-area workflow for preparing cases, recording
structured training decisions, and reviewing feedback. The repository includes a
versioned synthetic moderation policy, 20 synthetic cases, frozen built-in
references, and an explicitly labeled fixture-based mock recommendation. The
mock is not a live moderation model, expert opinion, or accuracy ground truth.

Structural contract errors reject a decision: required fields, escalation and
unclear reasons, category exclusivity, complete reasoning, and reviewer note must
be valid. Policy-guidance departures remain non-blocking. They are displayed and
retained with the first and final decisions, comparison, and export without
rewriting the user's judgment. Workspace-authored references are labeled
`self_authored` and are never presented as independent review.

Prepared workspace cases snapshot only successful batch records after an
explicit action. Training sessions freeze their policy and reference versions,
preserve immutable first decisions plus explicit final revisions, and keep
cancelled or restarted attempts separate. Summaries show field-level raw counts,
eligible denominators, exclusions, and sample warnings rather than a composite
score or certification claim.

The configurable defaults are 100 prepared cases, 50 cases per session, and 20
retained session attempts. All state is bounded, expiring process memory. Limits
block new creation without silently deleting older cases or summaries. CSV export
is explicit and auditable; user-derived source text, model signals, context notes,
and trusted metadata are excluded by default and require separate opt-in. See
[Moderation Training](docs/MODERATION_TRAINING.md) for the full contract.

## Support Triage

Milestone 10 adds a separate local Support Triage workbench with three areas:
Source & Routing Guide, Triage Workspace, and Summary & Export. It uses a
versioned project-authored synthetic guide and 22 synthetic tickets. Users may
also explicitly snapshot successfully parsed batch records, including records
whose sentiment or emotion inference failed. Source provenance remains visible,
and no triage decision writes back into batch, review, insight, or moderation
state.

Human decisions keep primary and secondary intents, issue category, urgency,
recommended queue, escalation, recommended next actions, reasons, and notes
separate. Incomplete but legal drafts are explicit. Finalization is atomic,
freezes guide provenance, and preserves the immutable first decision; later
changes are explicit revisions. Structural errors block invalid state, while
synthetic-guide warnings remain non-blocking and auditable.

Independent mode hides any deterministic fixture mock before first finalize.
The assisted simulation may show a mock first but never prefills the human form.
Human–mock agreement and override counts are descriptive, not accuracy, quality,
causality, or operator performance.

Triage state is bounded, expiring process memory: 200 tickets per workspace,
eight concurrent workspaces, and 30-minute sliding inactivity expiry by default.
Limits block creation rather than evicting existing work. CSV export is explicit,
formula-safe, and `no-store`. Built-in synthetic text may appear by default;
workspace-derived text, NLP signals, human review, context notes, and trusted
metadata are separate opt-ins. See
[Support Triage](docs/SUPPORT_TRIAGE.md) for the complete contract and
limitations.

Batch Results includes a linked Support Triage entry that preserves the active
temporary token. Tickets with no deterministic mock say that it is unavailable;
the assisted-mode explanation appears only when a suggestion actually exists.

Milestone 10 is the last completed planned feature milestone for the current
version. Feature Complete Review is completed, Feature Freeze is PASS,
Product Hardening is complete, Full Regression and Manual Acceptance is
PASS, and the Release Candidate Gate is PASS. An explicit Version / Delivery
Decision by the repository owner and release readiness itself remain later
gates. Deferred next-version candidates remain outside the current `0.10.0`
feature boundary. Detailed live execution state is maintained only in
[Project Status](PROJECT_STATUS.md).

## Core contracts

Milestone 2 introduces a model-library-independent core:

- `NormalizedTextInput` for platform-neutral text and safe metadata;
- compact sentiment and emotion taxonomies;
- normalized and model-native scores kept separately;
- traceable provider/model/revision metadata;
- `SentimentProvider` and `EmotionProvider` protocols;
- deterministic mock providers for fast tests;
- `AnalysisService` for provider-neutral orchestration.

The mock providers remain available for fast tests. They do not inspect meaning
and must never be presented as real predictions. See
[Core Contracts](docs/CONTRACTS.md) for the contract boundaries.

## Privacy and data

Do not commit real messages, platform exports, personal notes, databases,
credentials, model weights, or generated analysis results. The committed
`data/README.md` is documentation only; all other contents of `data/` are
ignored by default. Public examples must be synthetic and free of personal
information.

See [Privacy](docs/PRIVACY.md) and [Security](SECURITY.md) before working with
real text.

## Licensing

Project source code is licensed under the [MIT License](LICENSE). That license
does not apply to third-party model weights, datasets, or dependencies. Those
assets require separate review and attribution as described in
[Model Governance](docs/MODEL_GOVERNANCE.md) and
[Third-Party Notices](THIRD_PARTY_NOTICES.md).
