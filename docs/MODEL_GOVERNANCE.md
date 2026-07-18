# Model Governance

Milestone 3 approves one local English sentiment model. The complete selection
record, rejected candidates, immutable revisions, mapping, and limitations are
in [Milestone 3 Sentiment Model Audit](MODEL_AUDIT.md).

Before any model is approved, record and review:

- provider and canonical repository;
- model name and immutable revision;
- task and supported languages;
- native labels and application label mapping;
- model license and base-model license;
- intended use and material restrictions;
- attribution requirements;
- known limitations and evaluation evidence.

Models with missing, ambiguous, research-only, non-commercial, or otherwise
incompatible terms must not enter the main implementation. Model weights must be
downloaded from their licensed source and must never be committed to this
repository.

The approved provider fixes the full model revision and disables remote custom
code. Its cache is local and ignored. Routine tests inject a deterministic
runtime; the real-model smoke test is opt-in. Changing the model ID, revision,
native labels, loading format, or license requires a fresh audit.

The project's MIT License applies only to original project source code and
documentation. It does not relicense models, datasets, or dependencies.
