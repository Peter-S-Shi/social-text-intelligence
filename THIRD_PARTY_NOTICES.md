# Third-Party Notices

## Local web interface dependency

- Flask: https://palletsprojects.com/projects/flask/
- License: BSD-3-Clause
- Purpose: local HTTP routing and server-rendered interface

Flask is installed only through the `web` or `dev` optional extra and is not
bundled in this repository. Its transitive dependencies retain their own terms.

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

## V2 desktop shell dependency (M5.2)

### Qt for Python: PySide6-Essentials and shiboken6

- Packages: `PySide6-Essentials` and its dependency `shiboken6`, constrained to
  `>=6.11,<7` (6.11.2 was used for development and tests).
- Source: https://pypi.org/project/PySide6-Essentials/ (The Qt Company, Qt for
  Python).
- License declared by the installed package metadata:
  `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`. This project uses the
  **LGPL-3.0** route and keeps the Qt libraries as separate, replaceable files.
  Qt itself is also available under commercial terms, which this project does
  not use.
- Purpose: the native desktop shell and the model-provisioning windows.
- Installed only through the `desktop` or `dev` extra; it is not bundled in the
  repository, and no installer or frozen build exists yet.
- Qt modules imported by the application: `QtCore`, `QtGui`, and `QtWidgets`,
  and nothing else. The installed wheel carries more Qt modules than these, so
  the audit tracks the imported set: `tests/desktop/test_boundaries.py` fails if
  another Qt module is imported, so adding one (some Qt modules are GPL-only)
  forces a licence check first.

**Status of the LGPL obligations: tracked, not cleared.** M5.2 introduces the
dependency for development only. The mandatory pre-distribution LGPL compliance
gate (see [V2 Desktop Architecture Exploration](docs/V2_DESKTOP_ARCHITECTURE_EXPLORATION.md))
has **not** been performed and has **not** passed. No installer or build that
contains Qt may be distributed until it records at least: preserved copyright
and licence notices with a prominent LGPL notice, Qt source provision or a
written offer for the exact versions shipped, dynamic linking with replaceable
Qt libraries and the information needed to run a relinked build, no GPL-only Qt
module, and a distribution channel that adds no conflicting terms.

The desktop shell uses system font fallbacks (Georgia, Segoe UI, Consolas). The
web fonts used by the design prototypes are not bundled, and their licences have
not been verified.

## Milestone 2 baseline

The core runtime package has no mandatory third-party dependencies and includes
no models, model weights, or datasets.

Optional development tools are declared in `pyproject.toml`. Their licenses
remain the property of their respective authors and are not replaced by the
project's MIT License.

Future milestones must update this file when adding a runtime dependency, model,
or dataset. Each entry must identify its source, exact version or revision,
license, purpose, and any required attribution.

## Local language detection (M5.6)

### py3langid

- Package: `py3langid`, constrained to `>=0.4,<0.5` (0.4.0 was used for development and
  tests).
- Source: https://pypi.org/project/py3langid/ (a fork of `langid.py` by Marco Lui,
  forked and maintained by Adrien Barbaresi).
- License: BSD-3-Clause (the package's `LICENSE`; original `langid.py` code by Marco
  Lui and Tim Baldwin's research, modifications by the fork's author). The licence
  text must be preserved in any distribution.
- Runtime dependency: `numpy>=2.0`, installed with it. NumPy 2.5.1's metadata declares
  `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` (the main licence plus bundled
  components; the licence files ship in the wheel and must travel with any
  distribution that includes NumPy). The version is
  left to the resolver (NumPy 2.5+ requires Python 3.12 or later, so Python 3.11
  resolves to 2.4.x). STI imports NumPy nowhere; MyPy is told to skip NumPy's stubs
  (see `[tool.mypy]` in `pyproject.toml`), which is not a version restriction.
- Purpose: deciding, locally and offline, which language a text is written in, so
  the app can warn when the approved English models may not suit it. Nothing is
  sent anywhere and no model is downloaded: the statistical model ships inside the
  package as a compressed NumPy archive that is loaded without pickle.
- Installed only through the `language`, `desktop`, or `dev` extra; not bundled in the
  repository. If it is missing, the language check reports "unavailable".
- Residual note: the package's published model is trained on public corpora
  (Wikipedia article leads, Tatoeba sentences, CC100, GlotCC) that keep their own
  terms. STI redistributes none of those corpora, and the package declares the
  BSD-3-Clause licence for its code and bundled model. This is recorded rather than
  cleared: re-check it before any packaged distribution.

See [Language detection](docs/LANGUAGE_DETECTION.md) for the candidates considered, the
selection evidence, and the behaviour contract.
