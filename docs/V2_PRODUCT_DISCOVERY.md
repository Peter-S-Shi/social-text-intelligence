# V2 Product Discovery

Status: **Complete. Product Scope Gate: PASS (2026-10-06, owner decisions in
section 11).** Evidence date:
**2026-10-06**. This is the durable record of the V2 Product Discovery phase.
It makes no implementation, prototype, desktop-migration, or UI-redesign
change. The V1 `0.10.0` baseline and its Public Portfolio Delivery history
are immutable; V2 starts from V1 baseline `main` SHA
`5572b4b696edce646feb29795dad2a10f3be4a62`.

Live phase state is recorded only in [Project Status](../PROJECT_STATUS.md).
Stable principles remain in the [Project Charter](../PROJECT_CHARTER.md).

## 1. Scope and method

- **Approved V2 goals (given, not re-litigated):** desktop packaging and UI
  redesign. They are treated as delivery vehicles; no feature conclusion below
  depends on them.
- **Inputs:** repository truth (code, tests, docs, Git history), a live run of
  the real V1 product with its pinned models, and current vendor/project
  sources recorded in section 9.
- **Comparison level:** capability and workflow only. No competitor code,
  copy, or UI was used.
- **Evidence grades:** **A** = primary vendor/project page fetched on the
  evidence date; **B** = secondary or search-summary only (not load-bearing);
  **L** = locally measured in this repository; **H** = hypothesis, no evidence.
  Conclusions rest on A and L. B and H items are labelled where they appear.

## 2. V1 as it actually is (evidence L unless stated)

- Offline Flask app on `127.0.0.1`; four top-level navigation entries: Direct
  analysis, Batch CSV, Moderation Training, Support Triage. **Human Review and
  Insights are not top-level**; they exist only inside a Batch workspace.
- Two pinned local models: `cardiffnlp/twitter-roberta-base-sentiment-latest`
  and `SamLowe/roberta-base-go_emotions`, English only, 512-token complete-input
  contract (reject rather than truncate).
- All state is bounded, expiring **process memory** (30-minute sliding expiry
  for triage; no database, no autosave, no history). Export is explicit CSV.
- Test suite: 195 passed, 2 skipped (real-model tests are opt-in). Tests are
  about 5.7k lines.
- Code weight: `services/` core analysis is 24 lines, while moderation
  training (1,714), support triage (1,211), and insights (1,050) dominate.
  Most V1 code serves the peripheral workflows rather than the analysis core.
- Footprint relevant to desktop packaging: model cache about 1.4 GB, PyTorch
  about 0.5 GB, repository `.venv` about 0.9 GB. Measured here, not a packaging
  design.
- Real-model probe (five synthetic sentences, CPU, offline; **anecdotal, n=5,
  not an evaluation**):

| Input type | Observed output | Reading |
| --- | --- | --- |
| Sarcasm ("Brilliant work, truly" after data loss) | sentiment positive 0.57, emotion admiration | wrong direction |
| Mixed ("love this app but pricing makes me furious") | sentiment negative 0.84, dominant emotion joy | dominant-emotion headline contradicts the text |
| Slang praise ("so bad it's good, I'm dead") | negative 0.83, amusement | partly right, headline wrong |
| Calm threat with pleasantry | sentiment positive 0.69, neutral | model blind to threat, as the Charter already warns |
| French sentence (thanks, helpful) | neutral 0.50 via CLI | no unsupported-language signal on the CLI path |

- Model facts (A): the Cardiff model was trained on tweets from January 2018 to
  December 2021 (CC-BY-4.0). The SamLowe model card reports precision 0.575,
  recall 0.396, F1 0.450 at threshold 0.5, notes poorly performing labels, and
  suspects labelling errors in its Reddit training data (MIT).

## 3. Competitor landscape (capability level)

Categories were chosen by what STI actually does, not by name recognition.

| Category | Examples (evidence) | Overlap with STI | Where they are stronger | Where STI differs |
| --- | --- | --- | --- | --- |
| Cloud NLP APIs | Azure Language, Amazon Comprehend (A) | Sentiment on batches of text | Many languages (Comprehend: 12 languages, all for document sentiment; targeted sentiment English only), aspect/opinion mining, scale | Text never leaves the machine; pinned provenance; human review |
| Feedback analytics suites | Thematic, Qualtrics Text iQ (A) | Sentiment over feedback, group comparison | Themes/topics as the headline output, integrations, dashboards, 16 optimised languages (Qualtrics), manual sentiment override | Local, no subscription, per-row audit trail; no themes |
| Support platforms | Zendesk Intelligent Triage (A) | Intent/sentiment/urgency routing | Runs inside the ticket system, about 150 languages for classification, confidence fields | Human-led, offline, not tied to a ticket system; but its AI side is a fixture |
| Annotation tools | Prodigy, Label Studio, Argilla (A) | Human accept/correct of model predictions | Persistence, multi-annotator, model-assisted loops, dataset export | STI's review is purpose-fit to sentiment/emotion with agreement semantics |
| Moderation APIs and models | OpenAI Moderation, Azure Content Safety, Perspective, Detoxify models (A for Perspective, Unitary; B for OpenAI, Azure) | Moderation training only | Real classifiers, severity levels, custom categories | STI offers practice with synthetic policy, not detection |
| Research/QDA and no-code | Orange3-Text, ATLAS.ti/MAXQDA/NVivo (A for Orange, ATLAS.ti AI page; B otherwise) | Exploratory sentiment on a corpus | Lexicon methods (Orange), coding workflows, topic discovery | Model-based, with review layer; much narrower |
| Local LLM runtimes | Ollama (A) | Could do classification locally | Arbitrary labels and languages by prompt | Deterministic, pinned, auditable (but narrower) |

Key verified facts behind the table:

- **Perspective API ends:** service ends December 31, 2026; no migration
  support (primary page). The best-known free toxicity scorer is disappearing.
- **Azure sentiment and opinion mining retire March 31, 2029**, with Microsoft
  directing new work to "Foundry models" (primary Learn page). Even incumbents
  are moving off fixed-label classifiers, which pressures the commodity value
  of "a sentiment label".
- **Prodigy** states it runs fully on the user's machine, "never phones home",
  and can be air-gapped; one-time licence; LLM-assisted annotation built in.
  This is the closest philosophical competitor and it persists data.
- **Label Studio**: annotation review workflow is Enterprise-only (primary docs
  page). The open edition lacks the review loop STI ships.
- **Thematic** Foundation: USD 25,000/year, up to 25,000 comments, 3 datasets
  (primary pricing page). The paid market targets teams, not individuals.
- **Zendesk** triage uses the first public comment and subject only, with
  sentiment "calibrated for customer service" so an issue alone is not negative
  (primary help page). Calibration to the domain is a real quality lever STI
  lacks.

## 4. Adversarial Product Grill

### 4.1 What is commodity

- A three-way sentiment label and a confidence number. Every cloud API and
  feedback suite provides it; an LLM can approximate it with a prompt.
- Batch CSV in, filtered CSV out.
- Toxicity or policy scoring (free or cheap elsewhere; STI does not even offer
  it).
- Aggregate dashboards over labels.

### 4.2 What remains distinctive (supported)

1. **Privacy by construction, verifiably.** Offline, loopback-only,
   CSP-restricted, no telemetry. Prodigy matches the posture but is a general
   annotation tool; cloud suites cannot match it.
2. **Evidence discipline.** Complete-input contract (no silent truncation),
   pinned model revisions, immutable AI predictions beside separate human
   judgments, first-decision immutability, and "agreement, not accuracy"
   language. None of the competitors reviewed expose this as the product's
   spine.
3. **Review loop included in the free product.** Label Studio gates review
   behind Enterprise; Argilla and Prodigy require developer setup.
4. **Engineering credibility** as a public portfolio asset (gates, CI,
   hardening). This is real but is an owner value, not a user value.

### 4.3 Where V1 is weak or incoherent

1. **The core differentiator is buried.** Review and Insights sit inside Batch
   rather than at the top level; the visible navigation promotes the two
   weakest workflows (Moderation Training, Support Triage).
2. **Half the product is simulation.** Moderation and Triage run on synthetic
   cases and a fixture "mock". They teach a process but analyse nothing; a user
   with real tickets gets less than a spreadsheet. The Charter's "workbench"
   identity and these modes pull in different directions.
3. **Work is disposable.** Process-memory state with expiry means human review
   effort, the product's most valuable output, is lost unless exported before
   the session ends. Every annotation competitor persists.
4. **Headline model output can mislead.** The probe shows a dominant-emotion
   headline contradicting the text. The threshold-fallback semantics are
   documented but the headline is what users read. Whether this reflects real
   performance on typical feedback is **unknown** (no evaluation set exists;
   section 6).
5. **No language handling in practice.** English-only is stated, but the probe
   shows no explicit unsupported-language signal on the CLI path; cloud
   competitors cover 12 to 150 languages.
6. **No theme or topic discovery.** The headline deliverable of feedback
   analytics suites (themes) is absent; STI only compares user-supplied
   metadata groups.
7. **Model currency.** The sentiment model's training data ends December 2021.
8. **Effort misallocation.** Peripheral workflow services outweigh the analysis
   core several times over (section 2).

### 4.4 What users can already do better elsewhere

- Multilingual or domain-calibrated sentiment at scale: cloud APIs, Qualtrics,
  Zendesk.
- Team labelling, consensus, dataset building: Label Studio, Argilla, Prodigy.
- Real moderation detection: moderation APIs and open toxicity models.
- Thematic discovery: Thematic and similar suites.

STI should not compete on these axes.

### 4.4a Self-check corrections made during research

- An initial search summary attributed sarcasm-limit statements to ATLAS.ti. The
  primary AI page, fetched afterwards, contains no such statement; the claim was
  **dropped**.
- Search results suggested a third-party claim that Azure Content Moderator
  retires in March 2027. It is secondary and **not used**.
- An initial search returned a study comparing LLMs and fine-tuned models on
  sarcasm (a different task and data). It does not support any claim about STI
  models and was **not used** as evidence for or against an LLM provider.
- OpenAI's moderation page returned HTTP 403; OpenAI facts are graded B and are
  not load-bearing.

## 5. Retain, improve, remove, defer

| Capability | Disposition | Reason |
| --- | --- | --- |
| Local pinned sentiment + emotion pipeline and complete-input contract | **Retain** | Core distinctive asset |
| Direct analysis | **Retain, improve** | Add honest headline semantics (mixed signals, low-margin cases) |
| Batch CSV with row-level failure isolation | **Retain** | Needed input path |
| Human review with separate AI/human records and agreement semantics | **Retain, elevate** | Most defensible differentiator; currently hidden |
| Insights (descriptive, sample-aware) | **Retain, simplify** | Valuable but gated behind Batch and bulky |
| Moderation Training | **Defer decision to owner** | Simulation on synthetic data; see Gate Q2 |
| Support Triage | **Defer decision to owner** | Same; fixture "mock" is the weakest claim |
| Process-memory-only state | **Improve** | See direction D1 |
| Platform connectors, accounts, shared workspaces, hosted demo | **Remove from candidate list** | Out of Charter; incumbents own them |

## 6. Candidate V2 directions (prioritised)

Each lists evidence strength and the main risk. None is approved.

**D1. Persistent local projects (save, reopen, history).** Evidence: A for
competitor behaviour (Prodigy local storage, annotation tools persist); L for
V1 loss-on-expiry. Strongest, because it protects the human-review output.
Risk: data at rest conflicts with V1's no-persistence privacy posture; needs
explicit design (encryption options, ignore rules, delete controls) and an
owner decision. The Charter already permits additive SQLite.

**D2. Make review the product centre.** Top-level review and insight workflow
decoupled from Batch; reviewed-dataset export; per-project agreement over time.
Evidence: L (current IA), A (Label Studio paywall, Prodigy focus). Low risk;
mostly information architecture on top of existing services, and it aligns with
the approved UI redesign without being determined by it.

**D3. Own-data evaluation: "how well does this model fit my text?"** Reviewed
rows become a local evaluation set, so users see model-versus-human agreement
on their domain before trusting aggregates. Evidence: L (probe failure
modes; V1 has no evaluation set at all), A (SamLowe published metrics show
large per-label variance). Risk: statistical claims; keep the "agreement not
accuracy" discipline.

**D4. Language-aware handling and a validated French path.** Evidence: A that
competitors cover many languages; A that a multilingual Cardiff model exists
(French among eight languages) but **its licence was not verified**; H for
user demand. Step one is a small spike: detect-and-warn plus a licensed
multilingual candidate and evaluation set, no capability claim until validated
(Charter section 7).

**D5. Local theme discovery** (cluster and label recurring topics). Evidence:
A that themes are the headline of paid feedback suites; H that individual users
need it. Risk: new model system, quality, scope. Investigate only after D1 to
D3; needs a demand signal.

**D6. Transcript and long-form (SRT/VTT).** Existing deferred candidate.
Evidence for demand: none gathered (H). Keep deferred; revisit with a concrete
user case. Would require chunking against the 512-token contract.

**D7. Optional local LLM provider behind the existing provider protocol.**
Evidence: A that Prodigy integrates LLMs and Azure is steering sentiment to
foundation models; no evidence that it improves quality on STI's tasks. Risk:
non-determinism and provenance. Spike only; defer as a product direction.

**D8. Reframe Moderation and Triage.** Options in Gate Q2. A local toxicity
signal is attractive given Perspective's end of service (A), but the Unitary
multilingual model card warns of profanity bias toward vulnerable groups (A),
and the Charter forbids moderation enforcement. If pursued it must be advisory.

## 7. Rejected or deferred, with reasons

| Direction | Verdict | Reason |
| --- | --- | --- |
| Platform connectors (YouTube, Reddit, X) | Reject for V2 | Charter and ToS risk; user-supplied files suffice; no demand evidence |
| Accounts, cloud sync, team workspaces | Reject | Contradicts local-first identity; Label Studio, Argilla, Thematic own it |
| Hosted public demo | Reject | Charter non-goal; privacy story |
| Auto-moderation or auto-routing actions | Reject | Charter non-goals |
| Custom model training or fine-tuning inside the app | Defer | Prodigy territory; large scope; revisit after D3 |
| Composite scores, rankings, "accuracy" claims | Reject | Violates evidence discipline |
| Real-time dashboards, scheduled monitoring | Reject | Needs connectors and persistence at scale |
| Transcript analysis | Defer | D6 |
| LLM as primary engine | Defer | D7 |

## 8. Unknowns

1. **Real user need.** No user research exists; every demand claim above is
   either vendor positioning (A) or hypothesis (H). The owner is currently the
   only validated user.
2. **Model quality on realistic feedback.** The five-sentence probe is not an
   evaluation. D3 would answer this; until then do not claim fitness.
3. **Multilingual model licence and quality.** The cardiffnlp multilingual
   sentiment licence was not verified; no French emotion model was assessed.
4. **Desktop footprint.** Models plus PyTorch exceed 1.9 GB measured here;
   installer size, Python-embedding approach, and update story are engineering
   questions for a later phase, not discovery conclusions.
5. **Persistence privacy model** (D1): what is stored, how deleted, encrypted
   or not.
6. **Whether sentiment plus emotion beats a prompted local LLM** on the owner's
   texts: unmeasured.

## 9. Source provenance

All sources were accessed on 2026-10-06. Grade A: page fetched directly;
the cited claim is paraphrased from that page. Grade B: search-result summary
only.

| Claim | Source | Grade |
| --- | --- | --- |
| Perspective API ends Dec 31, 2026; no migration support | https://perspectiveapi.com/ | A |
| Azure sentiment/opinion mining retire Mar 31, 2029 | https://learn.microsoft.com/en-us/azure/ai-services/language-service/sentiment-opinion-mining/overview | A |
| Amazon Comprehend sentiment languages; targeted sentiment English only | https://docs.aws.amazon.com/comprehend/latest/dg/supported-languages.html | A |
| Qualtrics Text iQ sentiment scale, languages, manual override | https://www.qualtrics.com/support/survey-platform/data-and-analysis-module/text-iq/sentiment-analysis/ | A |
| Zendesk intelligent triage: plans, first comment only, about 150 languages | https://support.zendesk.com/hc/en-us/articles/4550640560538-Automatically-detecting-customer-intent-sentiment-and-language | A |
| Thematic Foundation USD 25,000/yr, 25,000 comments | https://getthematic.com/product/plan-and-pricing | A |
| Prodigy local, air-gapped, one-time licence, LLM assist | https://prodi.gy/ | A |
| Label Studio review workflow Enterprise-only | https://docs.humansignal.com/guide/quality | A |
| Argilla self-host/HF Spaces, text classification | https://raw.githubusercontent.com/argilla-io/argilla/main/README.md | A |
| Ollama local LLM runtime, MIT | https://github.com/ollama/ollama | A |
| Cardiff sentiment model data and licence | https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest | A |
| SamLowe emotion model metrics and limits | https://huggingface.co/SamLowe/roberta-base-go_emotions | A |
| Cardiff multilingual sentiment model (8 languages) | https://huggingface.co/cardiffnlp/twitter-xlm-roberta-base-sentiment | A (licence not captured) |
| Unitary multilingual toxicity model licence, bias warning | https://huggingface.co/unitary/multilingual-toxic-xlm-roberta | A |
| Prodigy stores annotations in SQLite/MySQL/PostgreSQL; Label Studio, Argilla persist datasets | search summaries and general tool descriptions | B (persistence is consistent across tools but not individually page-verified) |
| ATLAS.ti uses OpenAI GPT for AI coding | https://atlasti.com/ai-info | A |
| Orange3-Text 1.16.3 (2025-05-05), sentiment capability | https://pypi.org/project/Orange3-Text/ | A (methods detail B) |
| OpenAI Moderation API free, 13 categories | https://openai.com/index/upgrading-the-moderation-api-with-our-new-multimodal-moderation-model/ | B (fetch blocked, 403) |
| Azure AI Content Safety severity levels, custom categories | https://learn.microsoft.com/en-us/legal/cognitive-services/content-safety/transparency-note | B |
| NVivo/MAXQDA AI-assisted analysis | search summaries | B (not used as load-bearing) |

## 10. Product Gate brief

**Recommended V2 thesis.** *STI V2 is the private, local review workbench for
text evidence: bring a sensitive pile of feedback or comments, get honest model
signals, and turn them into human-verified, auditable, persistent findings,
without any text leaving the machine.* Compete on trust and review discipline,
not on label accuracy, language breadth, or team features.

**Prioritised directions.** D2 elevate review, D1 persistent projects, D3 own-
data evaluation (together these form the thesis); then D4 language-aware
handling with a validated French spike; D5, D6, D7 as evidence-gated
investigations; D8 per owner decision.

**Rejected or deferred.** Section 7.

**Decisions that require the repository owner (Product Scope gate).**

- **Q1. Persistence.** Approve local persistence (D1), which reopens the V1
  "no persistence" privacy posture? Recommendation: yes, additive SQLite in a
  git-ignored location with explicit delete, as the single largest V2 change.
- **Q2. Moderation Training and Support Triage.** Keep as-is, fold into one
  "Decision Practice" area, demote behind the review workflow, or retire from
  the main navigation? Recommendation: keep but demote and fold; do not invest
  in them further until real-data use is shown.
- **Q3. Language scope.** Is French (or multilingual) a V2 requirement, or
  honest English-only with unsupported-language warnings? Recommendation:
  warning and detection now; French only after the licence-and-evaluation spike.
- **Q4. Audience.** Is V2 for the owner and portfolio reviewers, or for outside
  users? This sets how much of D5 to D7 is justified. Recommendation: state it
  explicitly; absent user research, treat the owner plus reviewers as the
  audience and avoid speculative features.
- **Q5. Evidence standard for V2.** Must V2 include an evaluation on the
  owner's own texts before any capability claim? Recommendation: yes (D3).

Nothing else is escalated. The proposed ordering and the unknowns in section 8
are the discovery agent's judgment and may be overridden at the gate.

## 11. Product Scope Gate decision

**Status: PASS — 2026-10-06.** Sections 1 to 10 above are the discovery
evidence as submitted to the gate and are not rewritten. The repository owner
decided Q1 to Q5 as follows. This section is the authoritative disposition.

| Question | Decision | Binding consequence for V2 |
| --- | --- | --- |
| Q1 Persistence | **YES** | V2 introduces persistent local projects. Production data lives in an OS-appropriate per-user application-data directory, never inside the repository. SQLite is the current default direction, not a final design commitment. Explicit delete, retention, and export semantics are required. Encryption is neither claimed nor required yet; no document or UI may imply it. |
| Q2 Moderation Training and Support Triage | **KEEP + FOLD + DEMOTE** | Both remain as preserved secondary Decision Practice/Lab material, leave the main product centre, and receive no further V2 investment unless real-data value is later proven. |
| Q3 Language | **NO French requirement** | V2 requires language detection and an unsupported-language warning. French stays conditional on a future licence-and-evaluation spike (direction D4); no bilingual claim is allowed meanwhile. |
| Q4 Audience | **Repository owner and portfolio reviewers** | Applies until real user evidence exists. Speculative features (D5, D6, D7) stay evidence-gated. |
| Q5 Evidence standard | **YES, mandatory** | A representative-domain evaluation is a mandatory V2 evidence gate before any model capability claim. An own-data evaluation UI (D3) is not precommitted as a separate large feature; it may emerge from persistent projects plus human review. |

**Resulting V2 scope direction.** The thesis in section 10 stands. Committed
direction: D1 (persistent projects, with Q1 constraints), D2 (review as the
product centre), the language-detection warning from D4, and the Q5 evidence
gate. Demoted: D8 and the existing Moderation and Triage workflows. Still
evidence-gated, not committed: French (D4), themes (D5), transcripts (D6),
local LLM provider (D7). Rejections in section 7 are unchanged. Desktop
packaging and UI redesign remain approved V2 goals.

**What this gate does not decide.** Storage schema, desktop framework, packaging
approach, installer size strategy, migration of V1 in-memory workflows, and UI
design are open and belong to the next phase. This gate authorises no
implementation, prototype, or dependency change.

**Next phase: V2 Desktop Architecture Exploration**, preparing the Architecture
Gate. It must at minimum address: persistence design under Q1 (location, schema
direction, delete/retention/export), desktop packaging feasibility against the
measured footprint in section 8, how V1 services are reused, and how the Q5
evidence gate is enforced.
