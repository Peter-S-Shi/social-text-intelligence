# Model Provisioning Contract (V2-2)

This is the product and function contract for V2 model provisioning,
delivered by M5.0. It fixes what the feature does from the user's point of
view, so the desktop UI/UX design milestone (M5.1) can design the full
experience without inventing product semantics. The UI-neutral boundary that
implements the contract is `application/model_provisioning.py`. Its
filesystem and network details live in `infrastructure/model_store.py` and
`infrastructure/model_download.py`.

The contract follows the Architecture Gate decision A2 and the UI/IA Gate
decision U3 ([architecture record](V2_DESKTOP_ARCHITECTURE_EXPLORATION.md),
[UI/IA decision](V2_UI_IA_DECISION.md)).

## 1. Fixed decisions

These come from the gates and are not changed by this contract.

1. **Weights are not bundled.** They are fetched from each model's original
   licensed repository, or taken from a folder the user already has.
2. **Analysis never downloads.** Analysis runs only from verified local files.
   A missing or damaged model stops analysis with a clear message. It never
   triggers a download.
3. **Fixed models.** The provider, model id, immutable revision and licence of
   both approved models are fixed (table below). Nothing substitutes another
   model, revision, file format or provider: not automatically, not as a
   fallback, and not as a "repair".
4. **Recovery is required.** Interruption or failure leaves a state the user
   can recover from with an explicit action.
5. **Pause and resume.** These were only an implementation candidate. M5.0
   adopts them in one bounded form (section 6): stopping a download keeps the
   partial file, and the next download continues from it when the server
   allows. There is no separate "paused" state.

## 2. The approved models

Both models are required. Analysis needs both (Direct and Batch run sentiment
and emotion for every record).

| Key | Model | Revision | Licence | Files | Size |
| --- | --- | --- | --- | --- | --- |
| `sentiment` | `cardiffnlp/twitter-roberta-base-sentiment-latest` | `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7` | `CC-BY-4.0` | `config.json`, `merges.txt`, `pytorch_model.bin`, `special_tokens_map.json`, `vocab.json` | 502,401,839 bytes |
| `emotion` | `SamLowe/roberta-base-go_emotions` | `d75048347613a25d77de8cf6412eaae9fa7b26be` | `MIT` | `config.json`, `merges.txt`, `model.safetensors`, `special_tokens_map.json`, `tokenizer.json`, `tokenizer_config.json`, `vocab.json` | 502,063,093 bytes |

- **Total:** 1,004,464,932 bytes (about 0.94 GiB).
- **Manifest:** every file has a pinned size and SHA-256 hash in the code
  (`APPROVED_MODELS`). A file is accepted only if both match.
- **Licence ids:** the licence column uses SPDX identifiers, exactly as the
  code reports them.
- **Sentiment weights:** the sentiment model loads `pytorch_model.bin` at this
  revision, exactly as V1 does. The repository's separate `model.safetensors`
  belongs to a different revision and is not part of the manifest.

## 3. Where models live

- **Managed models folder:** `%LOCALAPPDATA%\SocialTextIntelligence\models`
  (`AppDataLocations.models_dir`). It is per user and does not roam.
- **Layout:** the Hugging Face cache layout,
  `models--<org>--<name>\snapshots\<revision>\<file>`. The existing providers
  therefore load it unchanged, in offline mode.
- **Staging:** partial and in-progress files live in `.sti-staging\` inside
  the same folder. They are never visible to the model loaders.
- **Writers:** the application writes this folder only through an explicit
  download or import, and every file is SHA-256 verified before it is put in
  place. It never deletes or rewrites anything there except staging files it
  created and installed files it is replacing on an explicit action.
- **User-supplied folders** are only read, never modified.

## 4. Readiness states

Each model has exactly one readiness state:

| State | Meaning | Analysis | Actions offered |
| --- | --- | --- | --- |
| `ready` | Every manifest file is installed with its exact size. Files were hash-verified when installed. | Allowed | Verify files, Open models folder |
| `not_installed` | No file of the pinned revision and no partial download | Blocked | Download, Use a models folder |
| `incomplete` | Some files are missing, and/or a partial download is waiting to be resumed. `resumable_bytes` reports the partial bytes held. | Blocked | Download (resumes), Discard partial download, Use a models folder |
| `corrupt` | An installed file has the wrong size, or failed hash verification during an explicit Verify | Blocked | Download (replaces only the bad files), Use a models folder |
| `wrong_revision` | Files exist only for a revision other than the pinned one | Blocked | Download (adds the pinned revision; the other revision is left alone and never used), Use a models folder |

- **Overall readiness** is "ready" only when both models are `ready`.
- **Other revisions:** each status also lists any other revision folders found
  (`other_revisions`). They are never loaded and never deleted.
- **Problem files:** `problem_files` names the manifest files that are missing
  or wrong. It never names user content.
- **Cost of a status check:**
  - Status is a quick check of presence and exact size; it never hashes
    gigabytes. It is safe on every launch.
  - Full SHA-256 verification runs after every download or import file, as
    part of every Download before an installed file is kept, and when the user
    asks for Verify.
  - A same-size damaged file can therefore show as `ready` until it is
    verified, or until model loading fails. That load failure is the existing
    `model_load_failed` error. The UI should then offer Verify.

## 5. First use

1. When the app starts it reads the status. Status reads nothing from the
   network and writes nothing.
2. If both models are `ready`, the app proceeds normally.
3. Otherwise the user sees the models' status and chooses:
   - **Download** (about 0.94 GiB from the original repositories);
   - **Use a models folder** they already have; or
   - **Later**: the app stays usable for browsing existing projects, but
     analysis is blocked (section 9).
4. Download needs an explicit user action. Nothing starts a download
   implicitly: not first launch, not analysis, not import.

## 6. Download

- **Scope:** Download covers every non-ready model, or a chosen subset.
  Inside each model it fetches only the missing or bad files. Files already
  installed are hash-verified first and kept if they match.
- **Source:** each file comes from
  `https://huggingface.co/<model>/resolve/<revision>/<file>` over HTTPS only.
  A redirect to a non-HTTPS address is refused.
- **Progress:** reported as `ProvisioningProgress` events:
  - `phase`: `verifying`, `downloading` or `copying`;
  - the model key and file name;
  - bytes done and total for the file, the model and the whole operation.
  The totals come from the manifest, so they are known before the first byte
  arrives. Model and overall bytes never move backwards. While re-reading a
  file to verify it, only the file count moves. During an explicit Verify,
  all three counts advance.
- **Cancel / stop:** the caller can cancel at any point, including while files
  are being hash-verified. Cancelling between files keeps finished files.
  Cancelling within a file keeps the partial download in staging. The result
  is `cancelled`. The model shows as `incomplete` with its `resumable_bytes`
  whenever anything was kept. If nothing was kept, it shows its earlier
  state.
- **Resume:** the next Download continues a partial file with an HTTP Range
  request. If the server ignores the range, that one file starts again from
  zero. Resuming is an optimisation only: every file is still verified in
  full before it is installed.
- **Installing:** a file is moved into place atomically only after its size
  and SHA-256 match. A failed hash discards that partial file (it cannot be
  resumed correctly) and the operation fails with `checksum_mismatch`.
- **One at a time:** only one download or import runs per process. A second
  request fails with `provisioning_in_progress`. Cross-process exclusion
  belongs to the deferred single-instance work from M4.

## 7. Use a models folder (offline / pre-provisioned)

For machines without network access, or for users who already have the files.
The user picks a folder. It may be:

- a Hugging Face cache folder (for example V1's `model_cache`, or the output
  of a Hugging Face download into a cache directory) containing
  `models--<org>--<name>\snapshots\<revision>\`;
- a folder that directly contains one model's files; or
- a folder whose immediate subfolders each contain one model's files.

A plain folder counts as a candidate for a model only if it contains that
model's weights file name (`pytorch_model.bin` for sentiment,
`model.safetensors` for emotion). This avoids reporting one model's shared
tokenizer files as a broken copy of the other model.

The process has three steps.

1. **Inspect (read-only, fast).** The result reports, per model, one of:
   - `found`: all files present with exact sizes, still to be hash-verified
     on import;
   - `incomplete`;
   - `mismatched`: the right file names with wrong sizes, so either damaged
     or a different revision;
   - `wrong_revision`: a cache folder that holds only other revisions;
   - `not_found`.

   The result also says whether the folder is recognisable at all. An
   unrecognisable folder is reported as unsupported. A folder that cannot be
   read fails with `source_unreadable`.
2. **Import.** Import copies each `found` model's files into the managed
   folder, hash-verifying while copying, with `copying` progress and cancel.
   - A hash mismatch stops the import with `checksum_mismatch`. Nothing from
     that file is installed. Files and models imported before it stay, and
     later models are not attempted. This is the same rule as for Download.
   - A cancelled or failed import removes its own partial copies.
   - The source folder is never changed.
3. **Afterwards.** The models are `ready`, and status, analysis and Verify
   behave exactly as after a download.

Using the models in place, without copying, is not offered. A copy means
deleting or moving the source later cannot break the app, and it keeps one
verified location.

## 8. Errors

Failures are typed `ModelProvisioningError` values. Each has a fixed code and
a fixed, content-free message, with no exception chain carrying paths,
addresses or server text.

- **Download and import** never raise for these failures. They return a
  `ProvisioningResult` with the outcome, the error code and message, and the
  fresh status afterwards, so the UI can offer the next action without
  guessing.
- **Inspecting a folder** raises `source_unreadable`.
- **Discarding partial downloads** raises `provisioning_in_progress` while an
  operation runs.
- **Programming errors** raise `ValueError`. These are an unknown model key,
  or importing a model that the inspection did not report as `found`. A UI
  never offers either.

| Code | When | State afterwards | Recovery |
| --- | --- | --- | --- |
| `network_unavailable` | No connection, DNS failure, timeout, connection dropped, or a body that ends before the manifest size | Partial kept: `incomplete` | Download again (resumes); or Use a models folder |
| `download_rejected` | HTTP error, an unexpected response, a non-HTTPS redirect, or a longer body than the manifest size | Partial of that file discarded | Download again later; or Use a models folder |
| `checksum_mismatch` | A downloaded or imported file does not match the pinned hash | That file discarded; earlier files kept | Download again; or a different models folder |
| `storage_failed` | The models folder cannot be created or written (disk full, permissions, or on Windows a file that a running analysis has loaded) | Whatever was installed is kept | Free space, fix permissions, or restart the app, then retry |
| `source_unreadable` | The chosen folder does not exist or cannot be read | Unchanged | Choose another folder |
| `provisioning_in_progress` | Another download or import is already running | Unchanged | Wait for it to finish |

When analysis is attempted while models are not ready, `ModelsNotReadyError`
(code `models_not_ready`) names the non-ready model keys. Its message is:
"The required local models are not ready. Download them or use a models folder
before analysing."

Batch analysis normally records a row-level provider error as a failed row.
M5.0 makes `models_not_ready` the exception. It propagates out of the batch
run, so the analysis lease is cancelled and nothing is committed (the M3/M4
atomic behaviour).

## 9. Analysis while models are not ready

- **Composition:** the desktop composition root uses
  `build_provisioned_analysis_service`. Before building providers, it requires
  both models to be `ready`. It then builds them against the managed folder
  with offline loading, so the loaders cannot reach the network.
- **Once per process:** readiness is checked when the analysis service is
  first built. A built service keeps its loaded models for the rest of the
  process. A later Verify that reports `corrupt` therefore takes effect for
  analysis on the next start, and the UI should say so.
- **When not ready:**
  - Direct analysis and Batch analysis fail with `models_not_ready` and
    change nothing.
  - Creating a project, importing and validating a CSV, opening, reviewing,
    exporting and deleting existing projects never need the models.
- **Separate error:** the missing runtime-dependency error (V1 F1.5,
  `missing_model_dependencies`) stays separate. A packaged desktop build
  bundles the runtime, so model readiness is about weights only.
- **Flask:** the frozen Flask surface keeps its V1 behaviour (V1 normal mode
  may download through the loaders). It is a development and compatibility
  surface and is not part of this contract.

## 10. Actions the desktop UI must expose

The M5.1 design must offer these actions, and only these, for provisioning.

| Action | Boundary call | Notes |
| --- | --- | --- |
| Show model status (both models, overall readiness) | `status()` | Always visible somewhere; the UI/IA baseline puts it in the sidebar footer |
| Download (all non-ready, or a single model) | `download(keys, on_progress, cancelled)` | Explicit only; shows the size before starting |
| Stop / cancel a running download or import | `cancelled` callback | Keeps finished files; the download partial is kept for resume |
| Resume | `download(...)` again | The same action as Download; offered when `incomplete` |
| Discard partial download | `discard_partial_downloads(keys)` | Deletes staging files only |
| Use a models folder: inspect | `inspect_folder(path)` | Read-only and fast; shows the per-model findings |
| Use a models folder: import | `import_folder(path, keys, on_progress, cancelled)` | Copies and verifies |
| Verify files | `verify(on_progress)` | Full hash check; can turn `ready` into `corrupt`. Not cancellable; about 1 GB of reading, so run it off the UI thread |
| Open models folder | `models_root` | Shows where the files are; deleting them by hand is the user's choice |
| Model details and provenance | `status()` fields | Model id, revision and licence (F1.4 / F4.8) |

**Out of scope for V2.0:**

- choosing a different model or revision;
- removing installed models from inside the app;
- changing the models folder location;
- proxy settings (the system proxy is used as-is);
- bandwidth limits;
- background or automatic updates.

## 11. Privacy

- Provisioning sends no user text anywhere and never touches project data.
- Network requests contain only the fixed model URLs.
- Nothing logs.
- Error messages are fixed and contain no paths, URLs, server responses or
  user content.

## 12. Test seams (M5.0)

| Seam | How it is tested |
| --- | --- |
| `ModelProvisioning` port, through `LocalModelProvisioner` | Real temporary filesystem plus an in-memory `DownloadTransport` fake serving synthetic manifest files. Covers every state, download, resume, cancel, failure, verify, discard, inspect and import |
| `UrllibDownloadTransport` | A local in-process HTTP server: ranges honoured and ignored, HTTP errors, refused redirects |
| Approved manifest | Literal ids, revisions, licences and sizes from this document |
| Analysis composition | `build_provisioned_analysis_service` refuses when not ready and uses offline settings when ready |
| Real models (opt-in) | Import from an existing local cache into a temporary managed folder, then offline analysis (`STI_RUN_MODEL_TESTS=1`) |
| Real network (opt-in) | Fetch the small pinned files over HTTPS, check them against the manifest, and resume by range (`STI_RUN_NETWORK_TESTS=1`) |
