# Architecture

## Milestone 3 boundary

Milestone 3 adds one licensed English sentiment provider behind the existing
model-independent contract. It intentionally adds no emotion model, combined
sentiment/emotion workflow, persistence, platform connector, batch workflow, or
user interface.

The current package contains:

- `foundation.py`: immutable project status and capability metadata;
- `cli.py`: diagnostics and one single-text sentiment command;
- `contracts/`: normalized input, result, provenance, and error contracts;
- `providers/`: stable protocols, deterministic testing implementations, and a
  pinned Cardiff NLP sentiment adapter;
- `services/`: provider-neutral analysis orchestration.

Dependency direction is `services -> providers -> contracts`. Contracts do not
depend on providers, model libraries, persistence, or UI code.

The optional Transformers/PyTorch runtime is imported lazily inside the concrete
provider. Installing the core or running fast tests therefore does not require a
model library or weight download. `SentimentAnalysisService` invokes only the
sentiment provider; the pre-existing combined mock service remains available for
future orchestration tests and is not used by the Milestone 3 workflow.

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
model revision only when `STI_RUN_MODEL_TESTS=1`. All fixtures are synthetic.
Private user text must never become a test fixture.
