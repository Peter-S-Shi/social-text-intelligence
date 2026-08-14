# Social Text Intelligence — Project Charter

## 1. Purpose of This Document

This document defines the long-term product vision, engineering philosophy, scope boundaries, architectural principles, and milestone-based development strategy for the `social-text-intelligence` repository.

It is intentionally broader and more detailed than future milestone prompts. Future milestone instructions should remain concise, outcome-oriented, and limited to the current development step. This charter should be used as the stable reference when making architectural or product decisions.

---

## 2. Project Identity

**Repository:** `social-text-intelligence`

**Working product name:** Social Text Intelligence

**Core positioning:**

> A privacy-conscious, locally executed NLP workbench for sentiment, emotion, and human-in-the-loop analysis of feedback, comments, transcripts, and social text using transparently licensed open-source models.

The project is not intended to be a simple sentiment-analysis demo or a one-page emotion detector. It should evolve into a coherent local-first text intelligence workbench that helps users:

- inspect sentiment and fine-grained emotions in text;
- analyze individual texts and batches of texts;
- understand language, tone, and community context;
- review and correct model predictions;
- practice policy-based content decisions;
- organize text-analysis results into useful, explainable workflows;
- evaluate where automated NLP succeeds and where human judgment remains necessary.

The product should remain understandable, reproducible, testable, and suitable for public GitHub presentation.

---

## 3. Core Project Philosophy

### 3.1 Independent implementation

The application must be independently designed and implemented.

External courses, tutorials, or demonstrations may provide high-level conceptual inspiration, but the repository must not directly copy or derive its implementation from proprietary educational materials.

The project must not copy:

- course repositories;
- course source code;
- course HTML, JavaScript, or UI layouts;
- instructional text;
- screenshots;
- project-specific test sentences;
- solution structures;
- branded assets;
- hosted course APIs.

The architecture, code, UI, tests, documentation, examples, and sample data should be created specifically for this repository.

IBM/Coursera materials are not project dependencies and should not appear in the repository as source assets.

### 3.2 Transparent model licensing

Every NLP model used by the application must have a clear and traceable license.

A model must not enter the main project unless:

- its repository declares an explicit license;
- the license permits the intended local inference and public-code use case;
- the base model license is compatible;
- material restrictions are understood;
- attribution requirements can be satisfied;
- the model source and exact revision can be recorded;
- the model is technically appropriate for the supported languages and labels.

Models with missing, ambiguous, research-only, or unsuitable terms must be excluded from the main implementation.

The source-code license of this repository does not relicense third-party model weights.

### 3.3 Privacy-first local inference

Local inference is the default product principle.

Whenever practical:

- text remains on the user's computer;
- text is not sent to external AI services;
- user inputs are not used for training;
- full text is not written to logs by default;
- private analysis data is stored only in local ignored files;
- no account, cloud database, or telemetry is required.

Privacy is not merely a technical detail. It is part of the product identity.

### 3.4 Human-in-the-loop judgment

The application should not imply that model predictions are objective truth.

Model outputs are probabilistic estimates. The system should preserve room for:

- human confirmation;
- human correction;
- uncertain or disputed labels;
- explanatory notes;
- review history;
- confidence inspection;
- comparison between model and human decisions.

The system should support AI-assisted judgment rather than fully automated judgment.

### 3.5 Reproducible, portfolio-quality engineering

The repository should demonstrate disciplined software engineering:

- modular architecture;
- explicit dependency management;
- automated tests;
- static analysis;
- deterministic data contracts where possible;
- clear model provenance;
- safe local data handling;
- meaningful Git history;
- documented limitations;
- reproducible setup.

The project should favor a small number of well-designed workflows over a large number of shallow features.

---

## 4. Primary Usage Model

The main use case is local personal use.

The application should run locally and be inspectable by another developer who clones the repository and follows the setup instructions.

Primary usage patterns:

1. The project owner runs the application locally for text exploration and practice.
2. A reviewer can inspect the repository, architecture, tests, screenshots, and model documentation.
3. An interested user can clone the source code and run the application on their own machine.
4. Model weights are downloaded from their original licensed source rather than committed to this repository.

The project does not require a publicly hosted service.

---

## 5. Non-Goals

The following are not part of the current main development direction:

- public SaaS operation;
- user authentication;
- cloud accounts;
- multi-tenant infrastructure;
- payment systems;
- online advertising;
- large-scale production deployment;
- direct redistribution of model weights;
- automated scraping of social platforms;
- automatic moderation enforcement;
- automatic deletion, banning, or publishing;
- medical or psychological diagnosis;
- personality inference;
- surveillance use;
- prediction of a person's true mental state;
- replacement of trained human moderators or support staff.

A public demo may be reconsidered later, but it must never become a hidden prerequisite for the core product.

---

## 6. Supported Text Domains

The analysis engine should remain platform-neutral.

Potential text sources include:

- direct text input;
- customer feedback;
- product reviews;
- survey responses;
- support messages;
- YouTube comments;
- YouTube transcript or subtitle files;
- Reddit posts and comments;
- X posts;
- forum discussions;
- community conversations;
- news comments;
- generic CSV or JSON text datasets.

The core NLP layer should not depend on any specific platform.

Platform integrations, if added later, should be optional input adapters rather than core dependencies.

The first versions should prefer user-provided text and files over automated platform retrieval.

---

## 7. Initial Language Direction

The architecture should support language metadata from the beginning.

Initial priorities:

- English as the first complete and validated analysis language;
- French as an intentional extension;
- no false claim of bilingual quality before French models and evaluation are validated.

The application should keep language detection or language selection separate from emotion classification.

Language-specific models may be used behind a shared provider interface.

The system should be able to record:

- detected or selected language;
- model used;
- model revision;
- supported label set;
- prediction confidence;
- unsupported-language warnings.

---

## 8. Analysis Taxonomy

### 8.1 Sentiment

The sentiment layer should support a compact polarity taxonomy such as:

- positive;
- negative;
- neutral.

If a chosen model uses a different native taxonomy, the mapping must be explicit and documented.

### 8.2 Fine-grained emotion

The visible MVP emotion taxonomy should remain useful without becoming unnecessarily large.

Recommended compact taxonomy:

**Positive**
- joy;
- amusement;
- admiration;
- gratitude.

**Negative**
- anger;
- sadness;
- fear;
- disgust.

**No clear emotional signal**
- neutral.

A more granular model may operate internally, but user-facing labels can be mapped into this compact taxonomy.

The application should preserve:

- dominant emotion;
- top secondary emotions;
- normalized emotion scores where meaningful;
- model-native labels for auditability;
- confidence or uncertainty information.

`Neutral` should be described as no clear emotional expression rather than as a literal emotion.

### 8.3 Mixed emotions

The application should not assume that every text contains only one meaningful emotion.

Where the model supports multi-label predictions, the system should preserve multiple emotion scores.

The UI should avoid reducing all analysis to a single dominant label.

---

## 9. Main Product Modes

The product should evolve around a shared text-analysis core and several coherent modes.

### 9.1 Explore & Insights Mode

Purpose:

- inspect individual or batch text;
- explore sentiment and emotions;
- compare communities or topics;
- examine trends;
- study language and tone.

Possible capabilities:

- direct text analysis;
- batch CSV analysis;
- emotion distribution;
- sentiment distribution;
- filtering;
- topic or source metadata;
- representative examples;
- transcript segmentation;
- time-based emotion timelines;
- exportable results.

### 9.2 Human Evaluation Mode

Purpose:

- compare AI predictions with human judgment;
- correct labels;
- track disagreement;
- practice annotation and quality review;
- study model limitations.

Possible workflow:

1. Display text.
2. Show model prediction and confidence.
3. Let the user accept, correct, or mark the case as unclear.
4. Record human labels and explanation.
5. Compare model and human outcomes.
6. Summarize disagreement and error patterns.

This mode may support:

- sentiment annotation;
- emotion annotation;
- relevance rating;
- content-quality checks;
- rubric-based review;
- confidence-based escalation.

### 9.3 Moderation Training Mode

Purpose:

- practice rule-based content decisions;
- distinguish emotional language from actual policy violations;
- document decisions and reasoning.

Possible decisions:

- allow;
- warn;
- remove;
- escalate;
- unclear / needs review.

Possible issue categories:

- no violation;
- harassment;
- hate or identity attack;
- threat;
- spam;
- personal information;
- sexual content;
- misinformation;
- off-topic content;
- community-specific rule violation.

The system must not automatically enforce decisions on real platforms.

### 9.4 Support Triage Mode

Purpose:

- classify feedback or support messages;
- identify intent and issue category;
- assess urgency;
- route text to a suggested workflow.

Possible outputs:

- issue category;
- intent;
- urgency;
- suggested queue;
- escalation flag;
- human notes.

The mode should assist organization and prioritization, not automatically send customer responses.

### 9.5 Culture & Community Explorer

Purpose:

- study English and French online community language;
- collect slang and recurring expressions;
- compare tone across communities;
- record model-versus-human interpretation.

Possible metadata:

- platform;
- community;
- language;
- topic;
- date;
- phrase or slang note;
- tone;
- cultural context;
- user's interpretation.

This mode should prioritize careful observation rather than claiming universal conclusions about a community.

---

## 10. Input Architecture

The application should use input adapters that convert different sources into a shared internal text record.

Potential adapters:

- direct text;
- multiline text;
- TXT;
- CSV;
- JSON;
- SRT;
- VTT;
- optional future YouTube comment connector;
- optional future Reddit connector;
- optional future X connector.

Each normalized record may include:

- record ID;
- text;
- source type;
- source label;
- language;
- timestamp;
- author identifier if supplied and safe;
- topic;
- community;
- parent record;
- optional user notes.

Platform-specific APIs should not be required for the application to function.

---

## 11. Data and Privacy Rules

### 11.1 Sensitive data must not be committed

Codex must prevent accidental Git inclusion of:

- local databases;
- uploaded text files;
- generated analysis datasets;
- private notes;
- API keys;
- tokens;
- `.env` files;
- absolute local paths;
- usernames embedded in configuration;
- machine-specific settings;
- model cache directories;
- IDE secrets;
- debug logs containing user text;
- personally identifying exports.

### 11.2 Sample data

Public sample data should be:

- synthetic;
- authored specifically for this project;
- clearly licensed;
- free of personal information;
- representative of useful edge cases.

Real social-platform content should not be copied into the repository merely because it is publicly visible.

### 11.3 Logging

Logs should avoid storing full user text by default.

Where debugging requires text inspection, the behavior should be explicit and easy to disable.

### 11.4 Local database

If local persistence is added, the database file must be ignored by Git.

Schema migrations should be additive and safe.

---

## 12. Model and Dependency Governance

A lightweight model registry should eventually record:

- provider or repository;
- model name;
- exact revision;
- task;
- supported language;
- native labels;
- application label mapping;
- license;
- base model;
- intended use;
- known limitations.

The repository should eventually include a third-party notice file that distinguishes:

- project source-code license;
- Python dependency licenses;
- model licenses;
- dataset licenses.

Dependency versions should be pinned or constrained deliberately.

The project should avoid adding a library when the same goal can be achieved clearly with the standard library or an existing dependency.

---

## 13. Architectural Principles

### 13.1 Separation of concerns

Keep the following layers separate:

1. input adapters;
2. text normalization and chunking;
3. model providers;
4. analysis services;
5. human review workflows;
6. persistence;
7. reporting and analytics;
8. UI.

The UI must not contain model-loading or database business logic.

### 13.2 Provider abstraction

Sentiment and emotion models should be accessed through stable interfaces.

Conceptual examples:

```python
class SentimentProvider:
    def analyze(self, text: str) -> SentimentResult:
        ...
```

```python
class EmotionProvider:
    def analyze(self, text: str) -> EmotionResult:
        ...
```

This permits future model changes without rewriting workflows or UI code.

### 13.3 Typed result contracts

Analysis results should use explicit schemas or typed objects.

Result contracts should separate:

- raw provider output;
- normalized application output;
- human-reviewed output.

### 13.4 Local-first persistence

Persistence should support local workflows without becoming tightly coupled to a specific UI framework.

SQLite is acceptable when structured history becomes necessary.

Plain JSON or CSV may be sufficient for early milestones.

### 13.5 Testability

Core analysis orchestration should be testable without downloading large models.

Tests should use mocks, fixtures, or lightweight deterministic providers where appropriate.

Model integration tests should be separated from fast unit tests.

---

## 14. User Interface Direction

The application should not copy the UI of any course project.

The interface should be designed around the product's own workflows.

Potential high-level navigation:

- Analyze;
- Batch;
- Explore;
- Human Review;
- Moderation Training;
- Support Triage;
- Insights;
- Models & Licensing;
- Settings / Data.

Not all pages should be introduced at once.

New pages should appear only when a milestone provides a complete workflow.

The application should avoid becoming one extremely long page.

The UI framework should remain an implementation choice rather than part of the product identity.

---

## 15. Explainability and Limitations

Every prediction should be presented as a model estimate.

The interface and documentation should make clear that:

- sentiment and emotion labels may be wrong;
- sarcasm and humor remain difficult;
- community slang changes over time;
- cultural context can alter meaning;
- emotion does not equal policy violation;
- negative sentiment does not imply harmful content;
- calm language may still contain threats or abuse;
- confidence values are not guarantees;
- the system does not determine a person's true psychological state.

The project must not market itself as a psychological assessment system.

---

## 16. Git and GitHub Development Policy

Development must follow a milestone-based Git history.

### 16.1 Repository synchronization

Codex is responsible for maintaining regular Git and GitHub synchronization during development.

For each completed milestone or coherent sub-milestone, Codex should:

1. inspect the repository state;
2. run relevant tests and checks;
3. review staged changes for accidental sensitive information;
4. update documentation where required;
5. create a meaningful commit;
6. push the commit to GitHub;
7. report the commit summary and verification results.

### 16.2 Sensitive-information review before every push

Before pushing, Codex must verify that tracked files do not expose:

- local usernames;
- personal email addresses unless intentionally public;
- machine names;
- private directory paths;
- authentication tokens;
- API credentials;
- browser data;
- private analysis inputs;
- private databases;
- personal exports;
- environment variables;
- hidden IDE or operating-system artifacts.

### 16.3 Commit quality

Commit history should communicate development progress.

Good examples:

- `chore: initialize local-first project foundation`
- `feat: add normalized sentiment result schema`
- `feat: add local emotion provider abstraction`
- `test: cover invalid and mixed-emotion inputs`
- `docs: document model license and limitations`

Avoid meaningless messages such as:

- `update`;
- `fix stuff`;
- `changes`;
- `final`.

### 16.4 Milestone completion review

Whenever the user states that a milestone has been completed, the repository should be inspected before proceeding.

The review should focus on:

- whether the milestone scope was actually completed;
- whether tests pass;
- whether architecture boundaries were preserved;
- whether sensitive files are excluded;
- whether documentation reflects the change;
- whether GitHub is synchronized.

Do not generate unnecessary rewrite suggestions when the implementation is already acceptable.

---

## 17. Milestone Development Philosophy

Development must advance through explicit milestones.

Each milestone should:

- have one coherent product outcome;
- preserve a runnable application;
- avoid speculative infrastructure;
- define scope boundaries;
- include acceptance criteria;
- include relevant tests;
- update documentation only as needed;
- conclude with Git/GitHub synchronization.

Future milestone prompts should not be exhaustive construction manuals. Codex should be trusted to choose reasonable implementation details within the stated architecture and constraints.

The milestone prompt should communicate:

1. objective;
2. product behavior;
3. architecture constraints;
4. explicit non-goals;
5. acceptance checks;
6. Git/GitHub completion requirements.

---

## 18. Completed Feature Boundary and Lifecycle Governance

The canonical mutable plan is [ROADMAP.md](ROADMAP.md). Current execution state
is recorded in [PROJECT_STATUS.md](PROJECT_STATUS.md). This Charter retains the
stable feature boundary, deferred categories, and gate-based delivery
principles; it is not the live status ledger.

**Stable feature boundary:** Milestones 1–10 define the implemented `0.10.0`
feature set. Milestone 10 is a temporary, human-led Support Triage workbench over a
versioned synthetic routing guide and ticket library. It supports explicit
snapshots of parsed Milestone 6 records even when NLP inference failed, while
keeping M3–M8 signals and notes as non-authoritative context. Draft, atomic
finalize, immutable first decision, explicit revision, guide provenance,
non-blocking guidance warnings, deterministic mock visibility, sample-aware
summaries, and privacy-default export remain separate and auditable. State is
bounded, expiring process memory with configurable blocking limits and no silent
eviction.

Former Milestones 11–12 are deferred next-version candidates. Former Milestone
13 is reclassified as lifecycle evaluation, hardening, acceptance, portfolio,
and delivery work rather than a next-version feature milestone. This stable
boundary does not broaden any completed milestone's scope. The Charter does not
record the live phase, gate outcome, blocker, PR, or release-readiness state;
those current facts are maintained only in
[PROJECT_STATUS.md](PROJECT_STATUS.md).

### Milestone 1 — Independent Local Project Foundation

Goal:

- initialize an original repository structure;
- establish the local application entry point;
- configure privacy-safe Git behavior;
- create testing and quality foundations;
- document project philosophy and scope.

No AI model integration is required yet unless a minimal stub is useful.

### Milestone 2 — Text Analysis Core Contracts

Goal:

- define normalized text input;
- define sentiment and emotion result schemas;
- create provider interfaces;
- support deterministic mock providers;
- establish validation and error contracts.

### Milestone 3 — Licensed Local Sentiment Analysis

Goal:

- select and document a clearly licensed sentiment model;
- integrate local inference;
- map native labels into the application taxonomy;
- expose single-text sentiment analysis;
- add model integration tests and limitations.

### Milestone 4 — Licensed Fine-Grained Emotion Analysis

Goal:

- select and document a clearly licensed emotion model;
- support the compact positive, negative, and neutral taxonomy;
- preserve top emotions and scores;
- combine sentiment and emotion into one report.

### Milestone 5 — Local Analysis Interface

Goal:

- provide a coherent user interface for direct text analysis;
- display sentiment, emotion, confidence, model identity, and limitations;
- handle invalid, unsupported, and oversized input safely.

### Milestone 6 — Batch Input and Export

Goal:

- accept structured user-provided files;
- analyze multiple records;
- show aggregate distributions;
- filter and export normalized results;
- keep uploaded content local and ignored by Git.

### Milestone 7 — Human-in-the-Loop Review

Goal:

- let the user accept, correct, or mark predictions as uncertain;
- preserve AI and human labels separately;
- track disagreement;
- summarize model-versus-human performance.

### Milestone 8 — Insights and Community Context

Goal:

- organize records by source, topic, language, platform, or community;
- support phrase and context notes;
- compare distributions across user-defined groups;
- avoid unsupported cultural generalizations.

### Milestone 9 — Moderation Training Workflow

Goal:

- provide policy-based training cases;
- record allow, warn, remove, escalate, or uncertain decisions;
- capture reasons and issue categories;
- keep AI advice subordinate to human judgment.

### Milestone 10 — Support Triage Workflow

Goal:

- classify issue type, intent, urgency, and suggested queue;
- support human review;
- generate structured summaries without automatically sending responses.

### Deferred next-version candidate — Transcript and Long-Form Analysis

Goal:

- accept SRT/VTT or long text;
- segment text safely;
- provide time- or segment-based sentiment and emotion views;
- summarize long-form trends without hiding segment detail.

### Deferred next-version candidate — French Capability

Goal:

- select and document suitable French or multilingual models;
- validate label mappings;
- compare performance across English and French;
- avoid declaring production-quality bilingual support without evidence.

### Deferred lifecycle work — Evaluation and Portfolio Polish

Goal:

- build a clearly licensed or synthetic evaluation set;
- report accuracy and class-level metrics where appropriate;
- document failure cases;
- finalize architecture diagrams, screenshots, model cards, notices, and reproducibility instructions.

Platform API connectors should be evaluated only after the local product is mature.

The gate-based lifecycle after Milestone 10 is:

1. Feature Complete Review;
2. Feature Freeze Gate;
3. Product Hardening;
4. Full regression and manual acceptance;
5. Release Candidate and packaging;
6. Deferred next-version backlog review.

None of these labels implies `1.0.0`, production readiness, public release, or
completion before its separate acceptance gate is satisfied.

The final feature milestone is not project completion. Feature Freeze requires
a formal recorded gate. Product Hardening must converge quality over the frozen
feature set and must not hide new feature development. Full automated
regression and manual acceptance are required before an RC decision. Any
reopening of frozen scope must be explicitly recorded with its rationale,
approved boundary, affected artifacts, and required regression.

---

## 19. Quality Gates

A milestone should not be considered complete unless relevant gates pass.

### Engineering gate

- application runs;
- tests pass;
- static analysis is acceptable;
- architecture boundaries remain intact;
- no obvious duplicate logic;
- errors are handled explicitly.

### Privacy gate

- no sensitive input is committed;
- local databases and uploads are ignored;
- no credentials are present;
- logs do not expose private text unintentionally.

### Licensing gate

- added models and datasets have documented licenses;
- model revision and source are recorded;
- attribution requirements are satisfied;
- no ambiguous model is treated as approved.

### Product gate

- the workflow is usable;
- labels are understandable;
- limitations are visible;
- AI output is not presented as unquestionable truth.

### GitHub gate

- changes are committed;
- commit message is meaningful;
- remote repository is synchronized;
- documentation is updated where necessary.

---

## 20. Decision Filter for New Features

Before adding a feature, ask:

1. Does it strengthen the core text-intelligence or human-review workflow?
2. Is its source and license clear?
3. Does it preserve privacy-first local use?
4. Can it be implemented without making the architecture platform-dependent?
5. Does it create a coherent workflow rather than a disconnected demo?
6. Is it appropriate for the current milestone?
7. Can it be tested and explained?

If the answer to several questions is no, the feature should be deferred or rejected.

---

## 21. Definition of Success

The project succeeds when it becomes a coherent, locally runnable NLP workbench that:

- performs reproducible sentiment and emotion analysis;
- uses transparently licensed models;
- protects user text by default;
- supports human correction and interpretation;
- demonstrates realistic text-analysis workflows;
- documents model limitations honestly;
- maintains clean modular code and tests;
- preserves a complete, privacy-safe milestone history on GitHub.

The final product should feel like an independently designed tool, not a repackaged course exercise and not a collection of unrelated AI demos.
