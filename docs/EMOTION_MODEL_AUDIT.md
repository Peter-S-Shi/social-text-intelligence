# Milestone 4 Emotion Model Audit

Audit date: 2026-07-18

## Decision

Milestone 4 approves
[`SamLowe/roberta-base-go_emotions`](https://huggingface.co/SamLowe/roberta-base-go_emotions)
for local English multi-label emotion inference at immutable revision
`d75048347613a25d77de8cf6412eaae9fa7b26be`.

The model repository includes and declares the MIT License. Its documented base,
[`FacebookAI/roberta-base`](https://huggingface.co/FacebookAI/roberta-base),
declares MIT at revision `e2da8e2f811d1448a5b465c236feacd80ffbac7b`.
The fine-tuning dataset,
[`google-research-datasets/go_emotions`](https://huggingface.co/datasets/google-research-datasets/go_emotions),
declares Apache-2.0 at revision
`add492243ff905527e67aeb8b80c082af02207c3`.

The model is technically suitable because:

- it was trained for multi-label classification of English Reddit comments;
- its 28 native labels include neutral and exact native counterparts for all
  eight non-neutral labels in the project's compact taxonomy;
- independent sigmoid probabilities preserve mixed-emotion signals;
- the repository provides `model.safetensors` at the approved revision;
- the standard Transformers RoBERTa implementation requires no remote code;
- model, base model, and dataset provenance and licenses are explicit.

The approved Safetensors file is approximately 499 MB and has upstream SHA-256
`84d6d338b4cf63f0ed3c990a0ce748d32d1d2965c072f4645accaa71af3888c0`.
The project downloads it from the original repository and does not redistribute
model weights or GoEmotions records.

## Candidate review

| Candidate | License and provenance | Multi-label, labels, and technical fit | Decision |
| --- | --- | --- | --- |
| `SamLowe/roberta-base-go_emotions` | MIT model, MIT base, Apache-2.0 dataset; immutable revisions available | English Reddit text; 28 labels; multi-label; native neutral; Safetensors | **Approved** |
| `cardiffnlp/twitter-roberta-base-emotion-latest` | MIT model with documented Cardiff base | English social text, multi-label, Safetensors; 11 labels but no neutral and no direct amusement, admiration, or gratitude | Rejected for compact-label incompatibility |
| `cardiffnlp/twitter-roberta-base-emotion-multilabel-latest` | No model license declared in repository metadata | English tweet model with 11 multi-label outputs but no neutral | Rejected for missing license and label incompatibility |
| `j-hartmann/emotion-english-distilroberta-base` | No model license declared in repository metadata | Seven single-label classes; not fine-grained multi-label output | Rejected for missing license and capability mismatch |
| `finiteautomata/bertweet-base-emotion-analysis` | No model license declared; associated project terms describe non-commercial/research use | English social-text fit, but restrictive or ambiguous terms | Rejected for licensing |
| `bhadresh-savani/distilbert-base-uncased-emotion` | Apache-2.0 declared | Six single-label classes, no neutral, and incomplete compact coverage | Rejected for label and multi-label incompatibility |

Rejected models are not fallback providers. Any future change to the approved
repository, revision, weights format, label mapping, or threshold requires a new
audit.

## Native labels and compact mapping

All 28 native probabilities remain in `native_scores` in the immutable model
configuration order. Compact scores use the maximum native probability within
each mapped group. Maximum aggregation preserves the 0-to-1 meaning of
independent probabilities and avoids inventing a probability by summing
overlapping multi-label signals.

| Compact label | Native labels |
| --- | --- |
| `joy` | `joy`, `excitement`, `love`, `optimism`, `relief` |
| `amusement` | `amusement` |
| `admiration` | `admiration`, `approval`, `pride` |
| `gratitude` | `gratitude` |
| `anger` | `anger`, `annoyance` |
| `sadness` | `sadness`, `disappointment`, `grief`, `remorse` |
| `fear` | `fear`, `nervousness` |
| `disgust` | `disgust` |
| `neutral` | `neutral` |

The native labels `caring`, `confusion`, `curiosity`, `desire`, `disapproval`,
`embarrassment`, `realization`, and `surprise` are intentionally not forced into
semantically different compact categories. They remain fully visible in native
scores for auditability.

## Threshold, dominant, secondary, and neutral semantics

The default threshold is `0.5`, matching the model card's standard binarization
example. The comparison is inclusive: a compact non-neutral score is active when
`score >= threshold`.

- The highest active compact non-neutral score is `dominant_emotion`.
- Other active compact non-neutral labels become `secondary_emotions`, ordered
  by descending score and then label for deterministic ties.
- If no mapped compact non-neutral score reaches the threshold, the dominant
  label is `neutral` and secondary emotions are empty.
- `confidence` is the compact score for the selected dominant label.
- Scores are independent multi-label probabilities and do not sum to one.

Neutral means only that no mapped compact non-neutral signal met the configured
threshold. It is not a literal emotion, proof that a person feels nothing, or a
psychological conclusion. A high unmapped native label can coexist with the
compact neutral fallback and remains visible in `native_scores`.

## Loading controls

The provider:

- fixes the full model revision;
- requires the upstream Safetensors file;
- sets `trust_remote_code=False`;
- requests the restricted `weights_only=True` loading path;
- imports optional model dependencies lazily;
- stores weights only in the ignored local cache;
- supports cache-only offline loading;
- keeps real-model tests opt-in.

## Intended use and limitations

The model supports exploratory analysis of one English social text at a time.
It does not infer a person's true feelings or mental state. Material limitations
include:

- GoEmotions contains approximately 58,000 English Reddit comments, so other
  platforms, communities, eras, and long-form domains may behave differently;
- sarcasm, humor, coded language, mixed context, and cultural variation remain
  difficult;
- model-card evaluation at threshold 0.5 reports overall F1 around 0.45, with
  substantial class imbalance and much weaker performance for rare labels;
- compact mapping loses distinctions and intentionally leaves eight native
  labels unmapped;
- inputs beyond the audited 512-token encoded limit are rejected before
  inference; no truncation or partial-text result is allowed;
- threshold choice changes recall, precision, dominant, and secondary outputs;
- outputs must not drive diagnosis, surveillance, or automatic moderation.

French is unsupported. Batch inference, persistence, and platform adapters are
outside Milestone 4.

## Primary sources

- [Approved model card](https://huggingface.co/SamLowe/roberta-base-go_emotions)
- [Approved immutable revision](https://huggingface.co/SamLowe/roberta-base-go_emotions/tree/d75048347613a25d77de8cf6412eaae9fa7b26be)
- [Base model](https://huggingface.co/FacebookAI/roberta-base)
- [GoEmotions dataset](https://huggingface.co/datasets/google-research-datasets/go_emotions)
- [Google Research GoEmotions publication](https://research.google/pubs/goemotions-a-dataset-of-fine-grained-emotions/)
