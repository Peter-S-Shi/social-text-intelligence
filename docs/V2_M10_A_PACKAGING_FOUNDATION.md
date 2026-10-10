# M10-A — Production Packaging Foundation

## Authority and boundaries

The owner explicitly reprioritized M10 engineering from `main@26e1d08`.
M9.0 remains a historical approved evidence design; M9.1 is COMPLETE and merged.
M9.2–M9.4 are **DEFERRED**, not accepted, waived or completed. Q5 real-domain
evidence is still required for model capability claims. The approved evidence
contracts and the completed 49-step M9.1 pack are unchanged.

This slice establishes an engineering foundation on the proven
[M7 Windows PyInstaller onedir route](V2_M7_FEASIBILITY_GATE.md), not a new
architecture decision or a distributable release. No installer, binary upload,
GitHub Release or LGPL-compliance conclusion is included. The optional
**30-minute owner packaged-app smoke remains planned NOT RUN**. Automated
bounded smoke is not that test, formal Windows UAT or accessibility acceptance.

## Repeatable build configuration

[tools/m10](../tools/m10/) contains the production-oriented spec, two entries,
build driver and exact build-environment dependency manifest. Python 3.12 x64
on Windows is the foundation target. The manifest pins the installed dependency
closure and PyInstaller/hook versions; it is not a hash-verified supply-chain lock
or a claim of byte-identical reproducibility across machines.

Create a dedicated build environment in a disposable generic location:

```powershell
py -3.12 -m venv .venv-build
.venv-build\Scripts\python -m pip install -r tools\m10\requirements-build.txt
.venv-build\Scripts\python tools\m10\build.py --output X:\sti-build-new
```

The driver requires Windows x64, Python 3.12 and exact manifest versions. It
fixes the initial source SHA and rejects staged, unstaged or untracked packaging
inputs (source, spec/tools and notices) before building; it rechecks inputs and SHA
after building. Unrelated governance edits are allowed. It
requires a short absolute output root (at most 60 characters) to leave room for
PyTorch nested license metadata. This conservative guard is not a general
Windows long-path guarantee. It always requires a **new** output directory; existing output/user data is neither
reused nor removed. Failed outputs remain for private diagnosis; use another
new directory after a repair. No automatic recursive cleanup is provided.
PyInstaller's build log contains machine paths and stays local/ignored.
The subprocess uses a controlled PATH containing only the selected Python and
Windows directories, a source-only PYTHONPATH, and removal of inherited
QT_PLUGIN_PATH and QML2_IMPORT_PATH overrides. Its Hugging Face cache is inside
the disposable build output and hub/model
network access is disabled. This prevents unrelated host native tools from
supplying conflicting DLLs; it is not a hermetic operating-system build or a
supply-chain security guarantee.

The spec resolves source relative to its own directory, explicitly includes
dynamic torch/Transformers/RoBERTa imports and their runtime metadata, and collects
the bundled py3langid resource. Required metadata failures abort the build rather
than silently omit dependencies. Framework/runtime binaries come from PyInstaller
hooks. Model weights and the Hugging Face cache are not data inputs to the spec.
Flask, developer test tooling and unused Qt WebEngine/QML/Quick modules are
excluded. The production UI entry and console check entry share one onedir
runtime; neither is an installer.

After building, the driver checks both executables and rejects known model weight
and database/environment file types. The layout audit is a bounded safeguard,
not a comprehensive privacy scanner or final license/compliance inventory.
`build-evidence.json` records source SHA, Python/platform, spec/manifest digests,
file count/size and explicit non-release status; generated evidence stays local.

## Packaged startup and offline diagnostic paths

```powershell
X:\sti-build-new\dist\sti-desktop\sti-check.exe --verify-runtime
X:\sti-build-new\dist\sti-desktop\sti-check.exe --smoke
X:\sti-build-new\dist\sti-desktop\sti-desktop.exe
```

For a development/QA environment with pytest installed, the actual frozen
regression is opt-in and uses the native Windows Qt platform plus fresh
application data:

```powershell
$env:STI_M10_BUNDLE = 'X:\sti-build-new\dist\sti-desktop'
python -m pytest tests\tools\test_m10_frozen.py
```

Linux/default CI explicitly skips these checks; it supplies no frozen Windows
runtime evidence. The two executables use complete Analysis resource lists and
COLLECT deduplication, avoiding cross-executable extraction references.

The packaged UI checks dynamic runtime availability before opening ordinary
per-user application data. Missing/unusable dependencies fail with a fixed native
Windows error dialog and exit 2; the application error does not echo the caught
exception or machine path. Third-party build/runtime diagnostics are not a
privacy-reviewed publication artifact.
The ordinary source `sti-desktop` entry is unchanged. This preflight imports heavy
libraries and therefore can affect startup time/memory; it does not load model
weights, download them, analyze user text or close the retained memory-floor risk.
Native-process crashes cannot be converted into a Python error by this check.

The console verifier exercises lazy model-loader classes, the RoBERTa module,
tokenizers/safetensors/hub, Qt imports and actual bundled language identification.
It prints bounded JSON and exit 0/2. It proves library/resource availability, not
model readiness, hash integrity, all optional imports or model capability.

The `--smoke` mode creates its own OS temporary directory, injects that root into
the existing desktop composition, shows/closes a real Qt window, verifies absent
external weights, imports a two-row synthetic CSV (one invalid), and reopens its
project. It never selects the production data directory or accepts an arbitrary
cleanup root. Its temporary data is removed by the standard temporary-directory
context; no actual user project or model cache is changed. It performs no network
request or model download/inference. It is deliberately bounded infrastructure
evidence, not a 30-minute manual trial.

## Evidence and remaining limitations

Observed on a Windows x64 development machine, not a clean machine or formal
owner acceptance:

| Check | Observed result |
| --- | --- |
| Actual Windows onedir build | PASS at `302d9f59af401126cb92e3a595622b80bcccf07b`; Python 3.12.14, PyInstaller 6.22.3/hooks 2026.8; 4,920 files, 683,536,087 bytes (about 652 MiB) |
| Spec / manifest SHA-256 | `57b539b032138639bb7e394e39023b6d8ed75587754662d92854f66aa548fca0` / `00d63116dcb0c7965144cf6f19cc104ef1c612bb009b8ad6a34f41d7fcdbc9fa` |
| Frozen offline runtime check | PASS: `ready=true`, `models_loaded=false`; actual dynamic model imports, Qt and language resource |
| Frozen native Windows Qt smoke | PASS: visible window, weights absent, 2 synthetic rows/1 invalid, project reopen; temporary application data and isolated offline hub cache |
| Opt-in frozen regression | 2 passed in 56.63 seconds, Windows Qt platform (not offscreen); this elapsed time is the pair of checks, not a startup benchmark |
| DLL closure proxy | PASS: 103 binaries scanned, no unresolved import library names against bundle/System32; not a complete symbol/compliance or clean-machine proof |
| Local full application regression | 1,165 passed / 4 existing opt-in skipped at application source `1233cfe`; subsequent packaging-only repairs did not change `src/` |
| Final focused regressions/static checks | 18 passed; Ruff, strict MyPy (236 files including build driver), compileall passed; two frozen tests explicitly skip by default |
| Fresh implementation-head CI | [Run 38085348126](https://github.com/Peter-S-Shi/social-text-intelligence/actions/runs/38085348126), `49f8771acb0ebc9b6f54d067a6861be5a944ee26`: Python 3.11/3.12/3.13 each 1,165 passed / 8 skipped, lint/type/compile PASS; Node 12 passed |
| Owner optional 30-minute trial / formal Windows UAT | Planned NOT RUN / NOT RUN |

The frozen artifact records its exact committed build SHA. The subsequent
SYSTEMROOT spelling normalization and governance closure do not relabel that
artifact as a build of a later SHA; Windows environment lookup is case-insensitive.
Linux CI runs regressions, static checks and compilation only; it does not build
or validate a Windows executable. Its eight skips are four existing model/network
opt-ins, two existing Windows-specific tests and the two actual-frozen checks.
The final documentation-only closeout uses `[skip ci]`; no implementation changes
follow the successful CI head. Independent Spec and Standards review findings
were repaired and re-reviewed. Current-state governance passes the audit question
"if this PR merged now, would every current-state statement still be true one
second later?" at 100% YES. This engineering review is not an owner acceptance
decision, LGPL approval or release authorization.

The real-build repair loop retained failed/superseded outputs privately: Windows
long license paths prompted the conservative short-root guard; cross-entry MERGE
references were removed in favor of shared-directory COLLECT; frozen Qt imports
then exposed an unrelated host-tool ICU 78 DLL collected through ambient PATH.
Its versioned symbols did not satisfy Qt's Windows ICU imports. A separate local
copy with only that conflicting DLL disabled passed the runtime check; the final
controlled-environment build passed both real frozen regressions. No host tool,
Windows configuration or production project was altered. Optional TensorBoard
collection warnings and Torch deprecation warnings did not block these bounded
checks; optional features were not exercised.

M7/M8 carry-forward dispositions remain authoritative: A3 integrity policy,
A5 memory floor/cold-cache/physical low-RAM, unexplained project availability,
unverified sync folders, the Qt teardown incident and Review text-size gaps are
not closed by packaging. Accepted UI deviations and bounded prior fixes remain
as recorded. See [M8 Track A](V2_M8_TRACK_A_LEDGER.md),
[Track B](V2_M8_TRACK_B_FIDELITY.md) and the historical
[M9 risk carry-forward](V2_M9_EVIDENCE_CONTRACT.md#risk-carry-forward-no-automatic-closure).

Final component/license inventory, Qt relinking/source/notice obligations,
Microsoft runtime redistribution, clean-machine checks, signing/SmartScreen,
installer/update/uninstall and authorized distribution remain later M10 gates.
Copying LICENSE and THIRD_PARTY_NOTICES into the build does not satisfy those
gates or establish LGPL compliance. Frozen TLS/download-resume and cached-model
inference on this production build require separate bounded evidence where not
observed; historical M7 inference is not automatically relabeled as new evidence.
No packaging result supplies deferred representative evaluation or owner M9.4
acceptance, and V2 remains **not release-ready**.
