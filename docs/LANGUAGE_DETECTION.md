# Language Detection and the Unsupported-Language Warning (V2-3)

Status: implemented in M5.6. This is the durable contract and evidence record for the
feature; the code is the source of truth for behaviour.

## What the feature is, and is not

STI runs a small **local, offline** language detector over each analysed text and
warns when the approved sentiment and emotion models do not support the language it
finds. The approved models are English models. The feature:

- **does** record, per analysed text, which language was detected, how the detector
  scored it, which detector and version produced it, and which languages the
  approved models support;
- **does** warn wherever model labels would otherwise be read without that context;
- **does not** translate, reclassify, hide, or change a label;
- **does not** block a text from being analysed;
- **does not** add French or any other language, switch models, or make any
  multilingual or bilingual capability claim (French stays conditional on a future
  licence-and-evaluation spike);
- **does not** say anything about who wrote a text: the notice describes the wording
  of the text only, never identity, nationality, culture, or intent.

## Supplied language and detected language are different facts

A CSV may carry a `language` column. That value is **trusted, imported metadata**. It
is stored and shown exactly as supplied and is what the Insights *Language* grouping
uses ("Language (as supplied in the file)"). It is never overwritten by detection.

Detection is separate evidence about the text, stored beside it on the immutable
analysis result. "Supplied language: en" and "Detected language: fr" can coexist, and
neither changes the other:

| Supplied | Detected | Result |
| --- | --- | --- |
| `en` | French | analysed; **warning**; grouped under `en` |
| `fr` | English | analysed; **no** unsupported-language warning; grouped under `fr` |
| none | any | grouped under *(not supplied)*, never `en` |

Model support comes from the models' own capability metadata
(`ProviderMetadata.supported_languages`; a language counts only if **both** approved
models support it), never from the detector's opinion of the models and never from a
CSV field. The analysis service no longer passes a supplied language tag to the models
at all: the models see the text only.

### Behaviour changes made with this feature

These were deliberate, and are the places a reviewer should look:

1. **A supplied non-English tag no longer blocks analysis.** Before M5.6 a row whose
   `language` column said, for example, `fr` was refused with the row error
   `unsupported_language`. That used a CSV field as the model-support decision, which
   is exactly the confusion this milestone removes, and it also meant the same French
   text was analysed when untagged but refused when tagged. The text is now analysed
   and judged from the text itself. The standalone provider classes still refuse an
   explicit non-English tag if called directly (the `sti sentiment` command), because
   that is their own contract.
2. **A missing language is no longer invented as English.** Batch import used to store
   `en` for an empty `language` cell, and direct analysis hard-coded `en`. Both now
   record no language. The Insights Language grouping reads the value exactly as the
   file supplied it, so older projects that stored an invented `en` regroup those rows
   under *(not supplied)* (the stored data is not rewritten).
3. **Older projects are never re-checked.** A result stored before M5.6 has no
   detected-language evidence. It opens as **not assessed**, with no warning and no
   claim about its language. Migration neither runs the detector nor invents English;
   the stored report simply has no `language` entry, which decodes as *not assessed*
   (no schema version change was needed).

## States

| Status | Meaning | Warns? |
| --- | --- | --- |
| `supported` | a language the approved models support was detected | no |
| `unsupported` | another language was detected | yes |
| `undetermined` | too little language to decide (short text, symbols, links, numbers) | yes |
| `not_assessed` / `not_run` | a result stored before language checks existed | no |
| `not_assessed` / `detector_unavailable` or `detector_failed` | a check was attempted and could not finish, or no detector was configured for a fresh analysis | yes |

A fresh analysis that has no detector configured is *unavailable*, not "not run": only a
result stored before M5.6 is ever "not run". A detector problem is a **result**, not an
error (this includes a detector that returns an answer that breaks the evidence
contract): analysis continues, the text is
never treated as supported, and the failure text (which could contain record text) is
not kept.

The detector's score is the package's own normalised score for its best language. It
is used to decide when to abstain and is shown only as "the detector's score", never
as a probability or as accuracy.

## Where the warning appears

Analyze one text; the analysed project summary (a count of texts that are not
confirmed as a supported language, naming the detected languages); each Review
record (beside, not inside, the read-only AI block, and apart from "Language supplied
in the file"); Insights (a project-wide caveat, a per-group "N of M analysed texts"
line that changes no metric or denominator, and a notice on every representative
case). The frozen Flask surface and the `sti analyze` command show the same wording.

Moderation Training and Support Triage freeze the language evidence into the record
snapshot they already freeze beside the AI signals, show its caveat where those signals
are shown, and add a `language_signal` column to their opt-in signals export (status,
detected language, score, reason, and detector in one cell, so a failed check is not
mistaken for a pre-M5.6 result); the
`language` in their trusted metadata is the supplied value only. Exports that carry
model evidence (normalized batch CSV, reviewed CSV, insights CSV with records) carry `detected_language`, `language_status`, `language_score`,
`language_reason`, and `language_detector` as columns **separate from** the supplied
`language` column; the insights export adds a note saying which is which.

Detected language is **not** an Insights grouping dimension.

## Detector selection (spike evidence)

Requirements: deterministic, local and offline, no model download at runtime, Python
3.11 to 3.13, a licence compatible with this MIT project, small enough to ship.

| Candidate | Licence | Python | Size | Outcome |
| --- | --- | --- | --- | --- |
| `lingua-language-detector` 2.2.0 | Apache-2.0 | **>= 3.12** | ~290 MB installed | rejected: excludes Python 3.11 and is very large |
| `langdetect` 1.0.9 | Apache-2.0 (package metadata says MIT; the shipped LICENSE and NOTICE are Apache-2.0) | pure Python | ~2.5 MB | rejected: non-deterministic unless seeded, unmaintained since 2021, inconsistent licence metadata |
| `pycld2` 0.42 | Apache-2.0 | wheels exist for 3.11 to 3.13 | native C++ extension | not selected: an opaque native extension of an unmaintained library, where a transparent pure-Python/NumPy detector meets the need (not evaluated further) |
| `gcld3` | Apache-2.0 | no wheel is published | needs a native build | rejected: not installable from a wheel |
| `fasttext` language-ID models | model published under CC BY-SA | needs a separate model download | separate file | rejected: a separately provisioned model |
| **`py3langid` 0.4.0** | **BSD-3-Clause** | **3.10 to 3.14** | **~4.5 MB** | **selected** |

`py3langid` (a maintained fork of `langid.py`) ships its statistical model inside the
package as an LZMA-compressed NumPy archive loaded with `allow_pickle=False`. There is
no network access and nothing to provision. It depends on `numpy >= 2.0` (BSD-3-Clause, with the bundled-component licences listed in
`THIRD_PARTY_NOTICES.md`), which
is installed with it; STI does not import NumPy itself. Its published model is trained
on public corpora (Wikipedia, Tatoeba, CC100, GlotCC); those corpora keep their own
terms, STI redistributes none of them, and the package declares BSD-3-Clause for the
code and bundled model. This residual note is recorded in `THIRD_PARTY_NOTICES.md`.

**Type checking and NumPy.** Installing NumPy made the CI type check fail on Python 3.12 and
3.13 (not on 3.11): pytest imports `ndarray` for typing only, MyPy followed it into NumPy's
stubs, and NumPy 2.5+ stubs use `type X = ...` statements, which are a syntax error under
the repository's deliberate `python_version = "3.11"` check level. Rather than raise that
level or cap a transitive runtime dependency, `pyproject.toml` stops MyPy at the NumPy
boundary (`follow_imports = "skip"` for `numpy`, with `follow_imports_for_stubs` so it applies
to `.pyi` files). That is safe only while nothing here uses NumPy, which
`tests/test_type_surface.py` enforces.

It is an **optional extra** (`pip install ".[language]"`, included in `desktop` and
`dev`). Without it the language check reports *unavailable* rather than answering.

## Bounded evaluation

`tests/language_eval_set.py` holds 74 invented texts (no real posts or people): 30 clear
English, 32 clear non-English across 21 languages and several scripts, and 12 with too
little language content (a single word, emoji, a URL, digits, a mention, punctuation).
The real-detector tests check that the warning policy behaves sensibly on each group:

| Group | Texts | Detector score range | Policy result |
| --- | --- | --- | --- |
| English | 30 | 0.947 to 1.000 | all `supported` |
| Non-English | 32 | 0.633 to 1.000 | all `unsupported` |
| Too little language | 12 | 0.014 to 0.159 | all `undetermined` |

The abstention threshold is **0.5**. This set is deliberately small and synthetic; it
shows the policy is reasonable, **not** that the detector is accurate. Short real
messages are the weak spot: very short English such as "Thanks!" or "Great service"
scores below the threshold and is shown as *not confidently determined*. That is the
intended behaviour (a caveat, not a guess). No accuracy claim is made.

## Layering

`contracts/language.py` (the immutable evidence and the `Detection` answer),
`providers/base.py` (the `LanguageDetector` port) and
`providers/language_py3langid.py` (the adapter) know nothing about widgets or
persistence. `services/language.py` holds the policy, the notice wording, the summary,
and the export columns. `AnalysisService` is the one place detection joins an analysis,
so direct analysis, persistent batch projects, the CLI and the frozen web surface share
the same semantics. Qt never calls the detector; it renders view models built from the
application-layer wording. Sentiment and emotion providers are never given the supplied
`language` tag (the analysis service removes it before they run); the record's other
fields, such as topic or community, are unchanged and no provider reads them.
