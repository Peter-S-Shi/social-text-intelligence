# Milestone 3 Sentiment Model Audit

Audit date: 2026-07-18

## Decision

Milestone 3 approves
[`cardiffnlp/twitter-roberta-base-sentiment-latest`](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest)
for local English sentiment inference at immutable revision
`3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7`.

The model repository declares CC BY 4.0. Its documented base model,
[`cardiffnlp/twitter-roberta-base-2021-124m`](https://huggingface.co/cardiffnlp/twitter-roberta-base-2021-124m),
declares MIT at revision `ca5834113201de5c7cfbc395a532c6adeeddfa83`.
The sentiment model was trained on approximately 124 million English tweets from
January 2018 through December 2021 and fine-tuned on the TweetEval sentiment
benchmark. The repository's immutable configuration declares the exact native
mapping `0 = negative`, `1 = neutral`, and `2 = positive`.

This is a strong fit because:

- the model and base-model licenses are explicit and traceable;
- CC BY 4.0 permits use and adaptation, including commercial use, with
  attribution and change-notice obligations;
- all three native labels map one-to-one to the application taxonomy;
- the model targets English social text, the first validated project language;
- the standard Transformers RoBERTa implementation requires no remote custom
  code;
- an immutable revision can be recorded with every result.

The project does not redistribute or modify the weights. It downloads the exact
revision from the original repository on first use and attributes Cardiff NLP in
`THIRD_PARTY_NOTICES.md`.

The model card identifies TweetEval as its fine-tuning benchmark. TweetEval is a
collection with subtask-specific terms; its dataset card identifies the
sentiment subset as CC BY 3.0 and also calls out the applicable platform terms.
Milestone 3 neither downloads nor redistributes TweetEval data. The dataset is
recorded here for provenance and must be separately reviewed before any future
training or evaluation use.

## Candidate review

| Candidate | License/provenance finding | Label and technical fit | Decision |
| --- | --- | --- | --- |
| `cardiffnlp/twitter-roberta-base-sentiment-latest` | CC BY 4.0 model; documented MIT base; exact revisions available | English social text; native negative/neutral/positive | **Approved** |
| `distilbert/distilbert-base-uncased-finetuned-sst-2-english` | Apache 2.0 model and documented DistilBERT provenance | English and smaller, but binary negative/positive output cannot preserve a model-native neutral class | Rejected for label incompatibility |
| `siebert/sentiment-roberta-large-english` | No license declared in repository metadata; an unresolved repository discussion requests a license | Binary output and substantially larger RoBERTa-large runtime | Rejected for missing license and label incompatibility |
| `finiteautomata/bertweet-base-sentiment-analysis` | No model license declared in repository metadata; model card describes the associated library as non-commercial/research-only and refers to third-party dataset terms | Native POS/NEG/NEU and social-text fit are good | Rejected because licensing is restrictive or ambiguous |
| `cardiffnlp/twitter-roberta-base-topic-sentiment-latest` | MIT declared | Target-based five-label task requires an explicit target and lacks a direct neutral class | Rejected for task and label incompatibility |

Rejected candidates must not be configured as fallbacks. A future model change
requires a new audit rather than silently changing the repository identifier or
revision.

## Loading and supply-chain controls

The approved immutable revision currently publishes PyTorch weights as
`pytorch_model.bin`, not Safetensors. This is a technical disadvantage. The
integration mitigates it by:

- fixing the full model commit hash;
- setting `trust_remote_code=False`;
- requesting the restricted `weights_only=True` PyTorch loading path;
- constraining the tested Transformers and PyTorch major versions;
- storing downloaded files only in an ignored local cache;
- keeping real-model tests opt-in so routine test runs do not download weights.

Safetensors would be preferable. If the upstream project publishes an official
Safetensors file, it must be reviewed at a new immutable revision before this
project switches to it.

## Mapping and output contract

The application preserves all native probabilities and maps them directly:

| Native label | Application label |
| --- | --- |
| `negative` | `negative` |
| `neutral` | `neutral` |
| `positive` | `positive` |

The provider rejects missing, non-finite, out-of-range, or non-normalized output.
The highest probability becomes the selected label and confidence. The result
also records provider name, model identifier, exact revision, supported
language, and native labels.

## Intended use and limitations

Milestone 3 supports one normalized English text at a time. The model is an
estimate suited to exploratory sentiment analysis, not an objective judgment.
Known limitations include:

- training data is social text ending in 2021 and language changes over time;
- sarcasm, irony, humor, mixed sentiment, slang, and community context can be
  misclassified;
- performance on long prose or domains unlike social text is not established;
- truncation occurs at the model's maximum supported input length;
- probabilities are model scores, not calibrated guarantees;
- the model must not be used for psychological diagnosis or automatic moderation.

English is the only approved language. French remains unsupported until its own
model selection and evaluation milestone.

## Primary sources

- [Approved model card](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest)
- [Approved immutable revision](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest/tree/3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7)
- [Documented base model](https://huggingface.co/cardiffnlp/twitter-roberta-base-2021-124m)
- [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)
- [TweetEval sentiment dataset licensing](https://huggingface.co/datasets/cardiffnlp/tweet_eval)
- [Transformers model-loading guidance](https://huggingface.co/docs/transformers/models)
