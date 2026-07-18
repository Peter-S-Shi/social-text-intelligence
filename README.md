# Social Text Intelligence

Social Text Intelligence is a privacy-conscious, local-first NLP workbench in
development. Its long-term purpose is to support sentiment, emotion, and
human-in-the-loop analysis of feedback, comments, transcripts, and other social
text with transparently licensed open-source models.

> **Status: Milestone 3 — licensed local sentiment analysis.** The project can
> analyze one English text locally with an immutable, attributed Cardiff NLP
> model revision. Emotion analysis and batch workflows are not yet implemented.

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

The first command invocation downloads the approved model revision from its
original Hugging Face repository into the ignored `model_cache/` directory.
Inference then runs on the local machine; input text is not sent to an inference
API. Use `--offline` after the model is cached to forbid network retrieval.

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
