# V2 M10 S1 — Optional language model (O1 + O2)

Status: **S1 implemented and verified on a real frozen build and a compiled
internal installer.** Binary distribution remains **BLOCKED**: B1 and B4 are still
derived, and B6 and the clean-machine matrix are open. `distribution_permitted`
stays false. Nothing was published or merged.

Plan: [Core + Optional Components plan, revision 2](V2_M10_CORE_OPTIONAL_PLAN.md)
§3.2 and §6 (S1), approved by the owner on 2026-10-11.

## 1. What changed

- **Core installer.**
  - It ships py3langid 0.4.0's code, metadata and BSD-3-Clause licence.
  - It does not ship the statistical model `data/model.npz.xz`, because the spec no
    longer collects the package's data files.
- **Optional model download** (setup and Models windows, "Language check model
  (optional)"):
  - It starts only when the user chooses to download.
  - The source is `https://raw.githubusercontent.com/adbar/py3langid/3b99caf00d0dcbc9416a9d06f8e5b690e919a74e/py3langid/data/model.npz.xz`,
    the commit of the `v0.4.0` tag.
  - It is HTTPS-only and can resume.
  - The file is installed only at exactly 4,586,720 bytes with SHA-256
    `f4f4a2c3…2963`.
  - Verify re-hashes the file and records damage.
  - It uses the existing model store with its own lock scope. It is not part of
    the sentiment/emotion readiness gate, so analysis never waits for it.
- **Detector** (`providers/language_py3langid.py`): the interface is unchanged. The
  model source order is:
  1. the package's own model (source installs, unchanged);
  2. else the separately installed file, only if its SHA-256 matches;
  3. else *unavailable*.

  A failed check is retried only after the installed file changes, so a batch never
  re-hashes it per text.
- **Packaged preflight.** The py3langid code is still required; the model is
  optional.
  - `sti-check --verify-runtime` adds `language_model_bundled`.
  - `sti-check --language-check <models folder>` is read-only and reports whether
    the check can run with that folder's model.
- **Compliance packet.**
  - `language_model` records whether the model is in the bundle, with the corpus
    terms marked "not verified".
  - B5 is derived only when the model is in the bundle. The default fails closed.
- **Docs.** `docs/LANGUAGE_DETECTION.md` and `THIRD_PARTY_NOTICES.md` are updated.

## 2. Contract preservation

Unchanged:

- the M5.6 states, the 0.5 threshold, the wording, the export columns and the
  snapshots;
- the "Language check unavailable" fallback;
- source installs;
- analysis behaviour.

One recorded difference: the `language_detector` evidence label names the model
source. A source install records "bundled statistical language model"; an installer
build with the downloaded model records "statistical language model installed
separately, SHA-256 verified". The detections are identical. A unit test checks the
74-text evaluation set against the bundled model.

## 3. Verification

| Check | Result |
| --- | --- |
| The approved single upstream download (tag URL) | 4,586,720 bytes; SHA-256 equals the pin |
| Final frozen build at `255e630` (official CPython 3.13.16) | 5,255 files, one fewer than M10-E2, about 4.56 MB smaller. **No `model.npz.xz` anywhere** |
| `--verify-runtime` / `--smoke` / `--license-info` | exit 0; `language_model_bundled: false` |
| Packet | valid; blockers **B1, B4** only (B5 not derived); `language_model.bundled: false`; py3langid BSD licence present |
| Frozen `--language-check` on an empty models folder | `available: false` (the unavailable fallback) |
| Installing the upstream bytes with the real model store (folder import, no network) | `not_installed` → `ready`, at the path the detector reads |
| Frozen `--language-check` after that | `available: true`; English → `en`, French → `fr`, the same as source mode |
| Opt-in frozen pytest (`STI_M10_BUNDLE`) | 2 passed |
| Compiled internal installer (Inno 6.7.3, per-user) | 5,257 payload files, none of them the model. A byte search for model content in the installer found none; the control search for the licence text found it |
| Local full suite | 1,253 passed, 6 opt-in skipped; Ruff and strict MyPy pass |
| Independent Spec and Standards reviews | findings fixed in `255e630`: bounded retries, label publish order, a Verify action, output shape, dead constant |

Evidence: [s1-frozen-receipt.json](evidence/m10-s1/s1-frozen-receipt.json). The
in-app download over the network was exercised with a synthetic transport only;
the one real download was the approved verification fetch.

## 4. B5, narrowly

The core installer does not redistribute the py3langid model, so B5 is not
derived for its contents. A user may obtain the model from its upstream publisher
by explicit choice. **Nothing here establishes that the training-corpus terms are
satisfied.** They stay recorded as unverified (M10-E2 §2.5), and the in-app text
says so.

## 5. Not done, and still open

- B1 (owner/legal position), B4 notice texts, and B6 (E4 with the owner's MSVC
  toolchain).
- The clean-machine matrix on an isolated VM, including the in-app language-model
  download.
- R2 stays parked in draft PR #62. Release gates are unchanged.
