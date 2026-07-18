# Model Governance

Milestones 3 and 4 approve one local English sentiment model and one local
English multi-label emotion model. Their complete selection records, rejected
candidates, immutable revisions, mappings, and limitations are in the
[Milestone 3 Sentiment Model Audit](MODEL_AUDIT.md) and
[Milestone 4 Emotion Model Audit](EMOTION_MODEL_AUDIT.md).

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

Approved providers fix full model revisions and disable remote custom code. The
emotion provider additionally requires the approved Safetensors artifact. Model
caches are local and ignored. Routine tests inject deterministic runtimes; real
model smoke tests are opt-in. Changing a model ID, revision, native labels,
mapping, threshold, loading format, or license requires a fresh audit.

The project's MIT License applies only to original project source code and
documentation. It does not relicense models, datasets, or dependencies.
