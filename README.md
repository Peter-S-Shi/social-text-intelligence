# Social Text Intelligence

Social Text Intelligence is a privacy-conscious, local-first NLP workbench in
development. Its long-term purpose is to support sentiment, emotion, and
human-in-the-loop analysis of feedback, comments, transcripts, and other social
text with transparently licensed open-source models.

> **Status: Milestone 7 — human-in-the-loop review.** The local Flask application
> supports direct English analysis, bounded CSV batch workspaces, independent
> sentiment and emotion review, honest agreement summaries, and explicit export.

## Principles

- Local inference is the default; user text should remain on the user's device.
- Model output is an estimate, not objective truth or psychological diagnosis.
- Every model and dataset must have a documented, compatible license.
- AI predictions and human-reviewed decisions must remain distinguishable.
- Platform integrations must be optional adapters, not core dependencies.

The stable product and engineering direction is defined in the
[Project Charter](PROJECT_CHARTER.md).

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

Run the local interface after installing the web and model extras:

```text
python -m pip install -e ".[web,sentiment,emotion]"
sti-web
```

Open `http://127.0.0.1:5000`. Use `sti-web --offline` after both pinned model
revisions are cached. The server binds only to the local loopback interface.

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

The default limits are 2 MiB, 500 rows, and 20,000 characters per text. Required
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
