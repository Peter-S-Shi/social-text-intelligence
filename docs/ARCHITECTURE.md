# Architecture

## Milestone 2 boundary

Milestone 2 adds typed, model-independent analysis contracts to the Milestone 1
repository foundation. It intentionally contains no real NLP model, persistence,
platform connector, batch workflow, or user interface.

The current package contains:

- `foundation.py`: immutable project status and capability metadata;
- `cli.py`: a dependency-free local diagnostic command;
- `contracts/`: normalized input, result, provenance, and error contracts;
- `providers/`: stable protocols and deterministic testing implementations;
- `services/`: provider-neutral analysis orchestration.

Dependency direction is `services -> providers -> contracts`. Contracts do not
depend on providers, model libraries, persistence, or UI code.

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
