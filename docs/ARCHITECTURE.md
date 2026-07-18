# Architecture

## Milestone 1 boundary

Milestone 1 establishes repository governance and a minimal executable package.
It intentionally contains no NLP model, text input contract, persistence,
analysis workflow, or user-interface implementation.

The current package contains only:

- `foundation.py`: immutable project status and capability metadata;
- `cli.py`: a dependency-free local diagnostic command;
- `__main__.py`: module execution support.

This small vertical slice proves packaging and test execution without creating
premature product abstractions.

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

Fast tests must run without network access or model downloads. Model integration
tests, when introduced, will be marked and separated from deterministic unit
tests. Private user text must never become a test fixture.
