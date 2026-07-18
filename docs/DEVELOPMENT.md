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

Run all checks before proposing a milestone commit:

```text
python -m unittest discover -s tests -v
python -m compileall -q src tests
ruff check .
mypy
```

The fast tests and compile check do not require model dependencies. GitHub
Actions runs the test, lint, type-check, and compile suite without downloading
model weights.

## Optional real-model validation

To validate the approved immutable revision locally:

```text
python -m pip install -e ".[dev,sentiment]"
STI_RUN_MODEL_TESTS=1 python -m pytest tests/integration
```

The first run downloads weights into ignored `model_cache/`. Set
`STI_MODEL_OFFLINE=1` after the cache exists to require offline loading. Never
commit model weights or caches.

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
