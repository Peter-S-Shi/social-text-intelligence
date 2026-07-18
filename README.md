# Social Text Intelligence

Social Text Intelligence is a privacy-conscious, local-first NLP workbench in
development. Its long-term purpose is to support sentiment, emotion, and
human-in-the-loop analysis of feedback, comments, transcripts, and other social
text with transparently licensed open-source models.

> **Status: Milestone 1 — independent local project foundation.** The project
> currently provides a runnable package, privacy protections, documentation, and
> automated quality checks. It does not yet perform text analysis.

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
```

Run the dependency-free test suite:

```text
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

For the complete contributor workflow, see
[Development](docs/DEVELOPMENT.md).

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
