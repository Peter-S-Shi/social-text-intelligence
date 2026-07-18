# Third-Party Notices

## Milestone 4 approved model

### Sam Lowe RoBERTa GoEmotions model

- Model: `SamLowe/roberta-base-go_emotions`
- Revision: `d75048347613a25d77de8cf6412eaae9fa7b26be`
- Author/provider: Sam Lowe
- Source: https://huggingface.co/SamLowe/roberta-base-go_emotions
- License declared and included by the model repository: MIT
- Documented base model: `FacebookAI/roberta-base`
- Base-model revision: `e2da8e2f811d1448a5b465c236feacd80ffbac7b`
- Base-model license declared by its repository: MIT
- Fine-tuning dataset: `google-research-datasets/go_emotions`
- Dataset revision: `add492243ff905527e67aeb8b80c082af02207c3`
- Dataset license declared by its repository: Apache License 2.0
- Approved weights: `model.safetensors`
- Upstream weights SHA-256:
  `84d6d338b4cf63f0ed3c990a0ce748d32d1d2965c072f4645accaa71af3888c0`
- Purpose: local English fine-grained multi-label emotion inference

The project uses the model unchanged for inference and does not redistribute its
weights or GoEmotions records. Sam Lowe, Meta, Google Research, Reddit, and
Hugging Face do not endorse this project. The model, base model, dataset, and
runtime dependencies retain their own licenses. See the
[Milestone 4 model audit](docs/EMOTION_MODEL_AUDIT.md) for provenance, candidate
decisions, mapping, threshold semantics, and limitations.

## Milestone 3 approved model

### Cardiff NLP Twitter-roBERTa sentiment model

- Model: `cardiffnlp/twitter-roberta-base-sentiment-latest`
- Revision: `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7`
- Authors/provider: Cardiff NLP
- Source: https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest
- License declared by the model repository: Creative Commons Attribution 4.0
- License: https://creativecommons.org/licenses/by/4.0/
- Documented base model: `cardiffnlp/twitter-roberta-base-2021-124m`
- Base-model revision: `ca5834113201de5c7cfbc395a532c6adeeddfa83`
- Base-model license declared by its repository: MIT
- Purpose: local English negative/neutral/positive sentiment inference

The project uses the model unchanged for inference and does not redistribute its
weights. Cardiff NLP does not endorse this project. Model weights retain their
own license and are downloaded from the original source. See the
[model audit](docs/MODEL_AUDIT.md) for attribution, provenance, mapping, and
limitations.

### Runtime libraries

- [Transformers](https://github.com/huggingface/transformers), constrained to
  `>=5.14,<6`, Apache License 2.0, used to load the standard RoBERTa tokenizer
  and model architecture.
- [PyTorch](https://github.com/pytorch/pytorch), constrained to `>=2.13,<3`,
  distributed under its upstream BSD-style project license and bundled
  third-party notices, used for local tensor inference.

These optional dependencies are installed through the `sentiment` and `emotion`
extras and are not bundled in the repository.

The approved model card identifies the TweetEval sentiment dataset as its
fine-tuning benchmark. The project does not download or redistribute that
dataset. Its sentiment subset and applicable platform terms are recorded in the
[model audit](docs/MODEL_AUDIT.md) for provenance only.

## Milestone 2 baseline

The core runtime package has no mandatory third-party dependencies and includes
no models, model weights, or datasets.

Optional development tools are declared in `pyproject.toml`. Their licenses
remain the property of their respective authors and are not replaced by the
project's MIT License.

Future milestones must update this file when adding a runtime dependency, model,
or dataset. Each entry must identify its source, exact version or revision,
license, purpose, and any required attribution.
