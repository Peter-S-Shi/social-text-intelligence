# V2 M10 — Core + Optional Components distribution plan

Status: **PLAN, revision 2 — approved by the owner (2026-10-11).** S1 is complete on
`main` (PR #64). S2 is implemented in draft PR #65: B4 is narrowed to the Intel
OpenMP terms. S3–S5 remain.
Documentation only. Nothing is implemented, built, published or merged by this
record, and no release gate changes. The owner's overriding goal is unchanged: a
legally distributable Windows installer, not a source-only portfolio.

Baseline: M10-E2 (PR #61, head `6179aa5`). The draft R2 work in PR #62 is parked
(§2).

## 1. Owner decisions (2026-10-11)

- **Approved: Core + Optional Components.** The main installer keeps every
  essential dependency whose redistribution obligations can be met, including the
  Qt/PySide6 stack under a completed LGPL route.
  - Qt is not externalized.
  - The desktop architecture is not redesigned because B1/B6 are still open.
- **Approved: the Visual C++ runtime stays on R1.**
  - No Microsoft runtime binary is shipped.
  - A missing prerequisite sends the user to Microsoft's official download, which
    may need administrator help.
- **Language detection is one release path (revision 2).**
  - Leaving the statistical model out of the core installer (O1) is only an
    intermediate packaging step.
  - The Q3 and M5.6 contract needs real language detection and unsupported-language
    warnings.
  - So the release ships optional, user-authorized provisioning of the model from a
    verified upstream source (O2), together with O1.
  - A desktop app that permanently reports "Language check unavailable" would be a
    product regression.
- **No liability transfer.** A separately downloadable add-on that STI packages or
  hosts still needs its own verified distribution rights.
- **Model weights** stay on the existing user-authorized provisioning path.
- **B1, B4 and B6** are finished through narrow, established tasks. No new
  installers are made for essential libraries.

## 2. Component disposition

| Component | Disposition | Open item |
| --- | --- | --- |
| Qt 6.11.2 / PySide6 / shiboken6 (LGPL-3.0) | **Core**: unchanged, replaceable loose binding layer | B1 owner/legal position; B6 E4 rebuild (§5) |
| Official CPython 3.13.16 (PSF) | **Core**: checked file by file | None (B3 closed in M10-E2) |
| PyTorch, transformers, tokenizers, safetensors, huggingface_hub, NumPy and other Python packages | **Core** | B4 notice texts (§5) |
| Intel OpenMP `libiomp5md.dll` / `libiompstubs5md.dll` (inside PyTorch) | **Core**: `torch_cpu.dll` imports it statically, so it cannot be optional | B4: the Intel licence text (§5) |
| py3langid 0.4.0 **code** (BSD-3-Clause; licence text shipped) | **Core**: the detector interface and its unavailable fallback stay | — |
| py3langid 0.4.0 **statistical model** `model.npz.xz` | **Optional**: not in the core installer; provisioned from upstream on user request (§3) | Owner agreement to this plan |
| Microsoft Visual C++ runtime | **External prerequisite (R1)**: not shipped; the installer stops and links to Microsoft | Clean-machine run of the missing-runtime branch |
| Route R2 (app-local runtime) | **Parked** in draft PR #62; no further work unless a concrete requirement reopens it | — |
| Sentiment and emotion model weights | **Unchanged**: downloaded only after user authorization; never bundled | — |

Intel OpenMP was checked for this table. The binary is Intel-signed, and its
version resource reads "Copyright (C) 1997, Intel Corporation. All rights
reserved". PyTorch's shipped `llvm-openmp` notice says it covers the macOS
`libomp`, not this Windows binary. So the Intel licence text really is missing.

## 3. Language model: feasibility and release path

### 3.1 Feasibility check (2026-10-11): PASS

The check used read-only metadata queries and local files only. Nothing was
downloaded.

| Question | Evidence | Result |
| --- | --- | --- |
| Is the exact 0.4.0 model published upstream on its own? | GitHub `adbar/py3langid`, tag `v0.4.0` (commit `3b99caf00d0dcbc9416a9d06f8e5b690e919a74e`) contains `py3langid/data/model.npz.xz`, 4,586,720 bytes. Its git blob SHA-1 `2221d7ba925849f78981d97d610fec208a89ed97` equals the blob SHA-1 computed from the installed file | Same bytes |
| Is there a usable download endpoint? | `https://raw.githubusercontent.com/adbar/py3langid/v0.4.0/py3langid/data/model.npz.xz` answers a HEAD request with HTTP 200, `application/octet-stream` and `Content-Length: 4586720`, so it is not a Git LFS pointer. The PyPI wheel `py3langid-0.4.0-py3-none-any.whl` (SHA-256 `c25bd038…0616`, 4,600,605 bytes) is a second possible source. It was not downloaded, so its contents are unchecked | One verified endpoint and one possible fallback |
| What is the pinned value? | SHA-256 `f4f4a2c3465ca1f081541037f9cac23021d68151c2f709c55ae5eedfca522963`, from the installed file and the package's `RECORD` | — |
| Does the existing API load an external model? | The py3langid code was copied without its `data` folder and imported in isolation. `LanguageIdentifier.from_model_file(<absolute path>, norm_probs=True)` then loaded a separately stored copy | English 0.998, French 0.999, "ok" 0.014 (below the 0.5 threshold, so *undetermined*). A missing file raises `FileNotFoundError`, which the adapter already maps to *unavailable* |
| Safety of the format | `modelio.load_model` reads LZMA plus `np.load(allow_pickle=False)`; no code is executed from the file | — |

**Confirmed in S1:** with the owner's approval, one full download through the
endpoint reproduced the pinned 4,586,720 bytes and SHA-256
([S1 record](V2_M10_S1_OPTIONAL_LANGUAGE_MODEL.md)). The feasibility rows above are
kept as recorded before that download.

### 3.2 Release path (O1 + O2 together)

- **Core installer.** It ships the py3langid code but not `data/model.npz.xz`, so
  the model is never redistributed by STI.
- **Optional provisioning.** On the user's explicit request, STI downloads the model
  from the upstream GitHub tag URL above, and the user is told the source. The
  download:
  - goes over HTTPS only;
  - checks the pinned size and SHA-256 before installing the file atomically into
    the local models folder;
  - is done once, and later starts are offline.
- **Independent of analysis.** The language model is **not** part of the
  sentiment/emotion readiness gate. Analysis never waits for it.
- **Without it,** the existing *unavailable* state applies unchanged ("Language
  check unavailable").
- **With it,** the existing detector, threshold 0.5, states, wording, exports and
  snapshots apply unchanged (`docs/LANGUAGE_DETECTION.md`).
- **Detector resolution order** (adapter only; the interface is unchanged):
  1. the package's own bundled model, when present. This is the path for source
     installs with the `language` extra, which stay unchanged;
  2. else the verified provisioned file;
  3. else *unavailable*.

  A provisioned file whose bytes differ from the pin is never loaded.
- **What B5 can claim, narrowly:**
  - STI's core installer does not redistribute the py3langid model, so B5 does not
    apply to the installer's contents.
  - The model reaches a device only from its upstream publisher, by the user's
    choice.
  - No claim is made about the training-corpus terms or about the user's rights to
    use the model. M10-E2 §2.5 records those as unverified.
  - The BSD-3-Clause notice for the shipped code stays in the packet.

### 3.3 If a later check fails

S1 stops, and the exact blocker is reported for an owner product decision, in any
of these cases:

- the full download does not reproduce the pinned bytes;
- the endpoint becomes unavailable;
- the external load fails in the frozen build.

Q3 is not dropped silently, and no alternative dependency research starts.

## 4. Real functional degradation

1. **Installed app before the user opts in.** Fresh analyses show "Language check
   unavailable".
   - This is the existing contract, and labels, metrics and analysis are unchanged.
   - After the user provisions the model, detection and the unsupported-language
     warnings are restored with the same semantics.
   - The cost is one extra user-authorized download of about 4.6 MB.
   - The model folder must be writable, which is already true for the model weights.
2. **Installation without the VC++ runtime (R1).** On a machine without the
   Visual C++ 2015–2022 x64 runtime 14.44+, the user must first install
   Microsoft's redistributable, usually with administrator rights.
3. **Nothing else.** Qt, sentiment and emotion models, source installs and analysis
   behaviour are unchanged.

## 5. Narrow tasks for B1, B4 and B6

- **B1 (owner/legal position, then small engineering).**
  - The bindings are unmodified upstream binaries built by The Qt Company.
  - The delivered `pyside-setup` source equals the `v6.11.2` tag: 4,600 of 4,602
    files are identical, and the other 2 are symlinks stored as file copies.
  - All 121 Qt files are verified against the official SBOMs.
  - Decision needed: accept that tag's source and build scripts as the
    Corresponding Source, and confirm the same-page source route.
  - **Recommendation:** accept.
- **B4 (engineering, with download approval).**
  - Fetch the licence texts of the 149 crates in the exact tokenizers `Cargo.lock`
    receipt (crates.io, pinned versions).
  - Obtain the Intel OpenMP licence that matches the shipped `libiomp5md.dll`
    (build 20260213).
  - PyTorch's static third-party content stays at the upstream-notice level.
- **B6 (owner toolchain, then the prepared run).**
  - The owner installs Visual Studio 2022 Build Tools (MSVC v143 14.44) with a
    Windows 11 SDK and accepts its licence.
  - Engineering then runs `tools/m10/e4_modified_qt.ps1` unchanged.
  - B6 closes only if the modified-source replacement passes.

## 6. Minimal executable change plan

| Step | Change | Files | Tests and evidence | CI |
| --- | --- | --- | --- | --- |
| **S1 — optional language model (O1 + O2)** — implemented, see [S1 record](V2_M10_S1_OPTIONAL_LANGUAGE_MODEL.md) | Frozen spec: ship py3langid code, exclude `data/model.npz.xz`. Adapter resolution order (§3.2). The preflight treats the language model as optional and reports its availability. A provisioning entry for the language model, separate from the analysis readiness gate. An opt-in UI action with the upstream source named. B5 derived only when the model file is in the bundle | `providers/language_py3langid.py`, `desktop/packaging.py`, the provisioning contract, store and transport (a generic pinned-URL entry beside the Hugging Face one), the desktop provisioning UI, `tools/m10/sti_desktop.spec`, `tools/m10/compliance.py`, notices, `docs/LANGUAGE_DETECTION.md` | Unit tests: resolution order; a bad hash is never loaded; absent model gives *unavailable*; provisioning success, failure and cancel; analysis is not gated by the language model; the existing language-warning suites unchanged. One approved real download reproduces the pinned SHA-256. Rebuild the frozen bundle: no model file in it; `--verify-runtime` and `--smoke` exit 0; *unavailable* before provisioning; after provisioning, the 74-text evaluation gives the same results as source mode; the packet derives B1 and B4 only | Yes (code) |
| S2 — B4 notices — implemented in draft PR #65, see [S2 record](V2_M10_S2_B4_NOTICES.md) | Add the crate licence texts and the Intel OpenMP licence to the packet; narrow the B4 derivation | `tools/m10/compliance.py`, `distribution/`, records | Packet test; rebuild | Yes |
| S3 — B6 E4 run | No code change expected | Receipt and records | E4 receipt; frozen checks on the modified bundle | Docs-only: no |
| S4 — B1 closure | Record the owner/legal position; the packet derives B1 from it | `tools/m10/compliance.py`, records | Packet test | Yes |
| S5 — clean-machine matrix (R1) | No code change expected | Evidence | `validate_installer.ps1 -EnvironmentKind DisposableVM`, including the missing-runtime prompt, a real model download and inference, and the language-model opt-in. Needs a VM or second PC: this host is Windows 11 Home, without Sandbox or Hyper-V | Docs-only: no |

**Order:**

- S1 ran after the owner agreed to this revision and approved the single model
  download; it is complete on `main`.
- S2 needs download approval, S3 the toolchain, S4 the B1 decision, and S5 a VM.

Lifecycle records are updated with each step. Documentation-only commits use
`[skip ci]`.

## 7. Stacked pull requests and merge order

| PR | Base | Content | Merge |
| --- | --- | --- | --- |
| #61 | `main` | M10-E2 blocker-closure engineering | **Merged first** (merge commit `bdf57dc`) |
| #63 | `milestone/m10-e2-blocker-closure` (#61) | This plan (docs only) | **Merged second**, after retargeting to `main` (merge commit `d50f05d`) |
| #64 | this plan's branch (#63) | S1 optional language model | **Merged third**, after retargeting to `main` |
| #62 | `milestone/m10-e2-blocker-closure` (#61) | Parked R2 | **Not merged.** It stays draft; if a requirement ever reopens it, rebase it onto `main` first |

The owner approved this sequence on 2026-10-11; merge commits keep the stacked
ancestry. Any further merge needs separate owner approval.

## 8. Not done by this plan

- No new installers for essential libraries.
- No Qt externalization.
- No further R2 work.
- No new open-ended legal or dependency research.
- No change to release gates.
- No merge and no publication.
