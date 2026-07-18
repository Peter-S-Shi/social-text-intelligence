# Model Governance

Milestone 2 does not include model dependencies or model weights. Its built-in
deterministic providers are test doubles, not NLP models.

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

The project's MIT License applies only to original project source code and
documentation. It does not relicense models, datasets, or dependencies.
