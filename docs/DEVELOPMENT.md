# Development

## Requirements

- Python 3.11 or newer
- Git

## Environment

Create and activate a repository-local virtual environment, then install the
development extras:

```text
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Quality checks

Run all checks before proposing a coherent milestone or lifecycle commit:

```text
python -m pytest -q
ruff check .
mypy --strict src tests
python -m compileall -q src tests
python -m pip check
```

The default suite does not require model downloads. GitHub Actions runs the
test, lint, type-check, and compile suite without downloading model weights.

## Optional real-model validation

To validate the approved immutable revision locally:

```text
python -m pip install -e ".[dev,sentiment,emotion]"
STI_RUN_MODEL_TESTS=1 python -m pytest tests/integration
```

The first run downloads both immutable model revisions into ignored
`model_cache/`. Set `STI_MODEL_OFFLINE=1` after the cache exists to require
offline loading. Never commit model weights or caches.

## Milestone discipline

Each milestone must have a coherent outcome, acceptance checks, privacy review,
and documentation updates where needed. Do not add models, datasets, UI pages,
or persistence before their milestone establishes the necessary contracts and
governance.

Before every commit or push:

1. inspect status and all staged and unstaged changes;
2. verify ignored local data and credentials;
3. search for secrets, personal information, machine-specific paths, and real
   user content;
4. run the relevant checks;
5. stage only the intended files.

## Lifecycle Phase Discipline

The mutable lifecycle plan is maintained in
[ROADMAP.md](../ROADMAP.md), current execution state in
[PROJECT_STATUS.md](../PROJECT_STATUS.md), and feature-scope findings in the
[Feature Complete Manual Audit](FEATURE_COMPLETE_MANUAL_AUDIT.md).

### Feature Complete Review

- perform a product-level audit before freeze;
- create one independently decidable finding per `FCR-XXX` audit item;
- classify each finding before implementation;
- update `docs/FEATURE_COMPLETE_MANUAL_AUDIT.md`;
- update `PROJECT_STATUS.md`.

### Feature Freeze

- freeze the approved current-version feature set through a formal gate;
- prohibit hidden feature expansion;
- record every reopening decision before implementation;
- require full regression after reopening.

### Product Hardening

- limit work to defects, usability, accessibility, privacy, error-state,
  consistency, performance, and bounded-capacity corrections;
- add no new product domain, language, model system, connector, account,
  persistence layer, or top-level workflow;
- update only the affected sections of the living
  [Manual QA artifact](../manual-qa/manual_review_questionnaire.html);
- update project status after each coherent hardening increment.

### Full Regression and Manual Acceptance

- complete the full automated validation suite;
- execute the living manual-QA artifact with representative synthetic data;
- record every blocker and its disposition;
- do not propose a release candidate while a release blocker remains.

### Release Candidate

- verify packaging, reproducibility, licenses, notices, privacy, and final
  regression;
- require an explicit RC gate;
- do not infer `1.0.0`, production readiness, or public release from RC status.

### Mandatory Status Updates

Every coherent lifecycle PR must update `PROJECT_STATUS.md` with the tested
revision, phase and gate states, blockers, latest validation, and next required
action.

## Local web interface

Install the local interface and model runtimes, then bind to loopback:

```text
python -m pip install -e ".[web,sentiment,emotion]"
sti-web
```

The first analysis lazily loads both models. Use `sti-web --offline` to require
an existing cache. Flask route tests inject deterministic providers and do not
download weights.

Windows reviewers may instead double-click `start_social_text_intelligence.bat`
from the repository root. The launcher resolves the local `.venv` relative to
itself, starts the same offline server, and opens the loopback URL; it performs
no installation or download.

Use `sti-web --help` to configure `--max-batch-bytes`, `--max-batch-rows`, and
`--max-text-length` for a local run. Defaults are 2 MiB, 500 rows, and 20,000
characters.

Batch service and route tests use only project-authored CSV bytes held in memory.
They cover column selection, validation, duplicate IDs, partial failure,
aggregates, filters, compact/native export, expiry, and file/row limits. Never
place real CSV uploads or generated exports in the repository.

Human-review tests use deterministic providers and synthetic review fixtures.
They cover independent judgment semantics, partial versus complete status,
multi-label validation and neutral exclusivity, immutable AI results, navigation,
filters, honest denominators, agreement calculations, reviewed export, formula
protection, no-store responses, and cleared workspace behavior. Browser checks
should exercise both desktop and narrow layouts without using real text or
metadata.

Insight tests use synthetic metadata and deterministic providers. They cover the
trusted grouping allowlist, metric/perspective compatibility, exact
denominators, filters, per-metric sample policy, definitive review semantics,
manual context-note validation, representative-case rules, explicit export,
formula protection, complete export audit counts, safe failed-row grouping,
timezone-aware export/note timestamps, no-store responses, workspace
clearing/expiry, and accessibility-oriented route content. Browser checks should
exercise the explorer, notes, examples, and
export views at desktop and narrow widths with no external requests or console
errors.
