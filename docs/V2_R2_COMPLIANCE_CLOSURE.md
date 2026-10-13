# V2 Release-2 — Distribution compliance closure (engineering)

Status: **engineering complete; B1 and B4 remain legally OPEN;
`distribution_permitted` stays false.**

This milestone builds the smallest auditable route for each remaining blocker:

- **Intel OpenMP (B4):** a NuGet-sourced redistribution route.
- **Qt/PySide6 (B1):** the release-facing source-access materials.
- **D4:** a bounded record of the remaining owner/legal decisions.

It grants nothing:

- no record in this repository can clear B1 or B4, or permit distribution;
- such a change needs a separately authorized legal decision and a reviewed
  code change.

Unchanged:

- Release-1 remains an owner-approved CONDITIONAL exit;
- B6 stays closed only on its QtCore-only criterion;
- M9.2–M9.4 stay DEFERRED;
- R2 (draft PR #62) is untouched.

## 1. Intel OpenMP from Intel's NuGet package (B4)

### 1.1 Evidence

The evidence was gathered on 2026-10-13. The single package download was
approved by the owner. The raw evidence stays private on the host.

| Fact | Result |
| --- | --- |
| Package | `intelopenmp.redist.win` 2026.1.0.239 from nuget.org; account owner "Intel" |
| Package hash | 2,163,555 bytes; SHA-512 equals the NuGet catalog `packageHash`; SHA-256 `2a0f9fcd…99fe` |
| Author signature | Primary signer: an Intel Corporation EV code-signing certificate (SHA-256 `69fce007…b5fa`), commitment *proof of origin*. The CMS signature is valid. The signed package hash equals the recomputed unsigned-package hash. The chain was verified to Windows trusted roots; revocation was not checked |
| Repository countersignature | NuGet.org Repository by Microsoft, *proof of receipt*. Structure inspected; its cryptography was not independently verified |
| Byte identity | `libiomp5md.dll` and `libiompstubs5md.dll` in the package are byte-identical to the frozen candidate `a16d559` and to the earlier provenance record |
| Licence in the package | `license.txt` (SHA-256 `6c00ae54…7c97`) is the Intel Simplified Software License (Version October 2022). `third-party-programs.txt` is byte-identical to the copy already in the packet |

Matching bytes do not carry rights over from the PyPI/PyTorch channel, where
the same files came under the Intel End User License Agreement for Developer
Tools. The route therefore ships the copies taken from the NuGet package, and
names that package's licence.

### 1.2 What the build now does

- **Pin.** `distribution/legal/intel-openmp/provenance.json` (schema 2) pins:
  - the package's size, SHA-256 and SHA-512;
  - the SHA-256 of the four entries used (the two DLLs, `license.txt` and
    `third-party-programs.txt`);
  - a description of the verified author signature.
- **Build (`build.py`, `source_intel_openmp`).** After PyInstaller, the build:
  1. reads the package from the build source directory and verifies the pin;
  2. checks that PyTorch's copies are the same Intel build;
  3. writes the package's bytes over them, and records the result in
     `build-evidence.json` under `intel_openmp_from_nuget`.
- **Packet assembly (`compliance.py`, `verify_intel_source`).** It independently
  refuses a bundle whose Intel DLLs are not the package's copies.
- **B4 status (`intel_openmp_status`).**
  - It adds a gap if the record does not name the pinned NuGet source, or names
    another licence.
  - It **always** adds the B4 Intel item, now worded as the remaining legal
    confirmations.

**Fail-closed cases, each covered by a test:**

- missing package;
- wrong size, SHA-256 or SHA-512;
- an altered, absent or duplicated pinned entry;
- a different Intel build in PyTorch;
- a missing DLL;
- a bundle DLL that is not the package's copy;
- a record that names the PyPI channel.

### 1.3 Packet changes

| File | Change |
| --- | --- |
| `legal/intel-openmp/INTEL-SIMPLIFIED-SOFTWARE-LICENSE.txt` | New. The package's `license.txt`, byte for byte |
| `legal/intel-openmp/LICENSE.txt` | Removed: it was the wheel's Developer Tools EULA. `provenance.json` keeps that route only under `superseded` |
| `legal/intel-openmp/third-party-programs.txt` | Unchanged; byte-identical to the package's copy |
| `legal/intel-openmp/NOTICE.md` | New. "Copyright Intel Corporation." (the package's nuspec copyright), the licence name and the scope of Intel's terms (§2) |
| `legal/intel-openmp/provenance.json` | Schema 2: NuGet source pin, ISSL licence, superseded EULA route, open legal items |
| `legal/THIRD_PARTY_ATTRIBUTIONS.md` | Intel section describes the NuGet route |

## 2. D4: Intel terms versus the Qt LGPL

The ISSL forbids modifying, reverse engineering, decompiling or disassembling
"the Software". In this distribution, that means the two Intel DLLs.

LGPLv3 §4 requires that the terms for the combined work do not restrict
modification of the Qt library portions, or reverse engineering for debugging
such modifications.

The engineering response sets the boundary in writing, in three places:

- `legal/intel-openmp/NOTICE.md`;
- `legal/QT_NOTICE.md`;
- the in-app licence notice (`desktop/license_notice.py`).

Each states that Intel's terms cover only `libiomp5md.dll` and
`libiompstubs5md.dll`, do not apply to Qt, PySide6, shiboken6 or the
application, and do not limit the LGPL rights.

The Intel DLLs are loaded by PyTorch, not by the Qt libraries. Whether this
scoping is legally sufficient is decision L3 below. It is not decided here.

## 3. B1: review and release-facing source-access materials

### 3.1 Evidence reviewed once

| Item | State | Since S4 |
| --- | --- | --- |
| Qt libraries, plugins and translations | Match the official Qt 6.11.2 build SBOMs; QtBase/QtSvg by commit, QtImageFormats/QtTranslations by version | unchanged |
| PySide6-Essentials / shiboken6 6.11.2 binaries | Byte-identical to the official wheels | unchanged |
| Binding producer record | None in the wheels. PyPI publishes no PEP 740 provenance for the two win_amd64 wheels (checked 2026-10-13) | no new evidence |
| `pyside-setup` 6.11.2 source | Equal to the `v6.11.2` tag tree | unchanged |
| Owner direction D1–D3 | Approved as an engineering direction only (`B1_OWNER_DECISION.json`); legal confirmation pending | unchanged |

No rebuild of Qt or PySide6 is proposed, because none of the evidence
demonstrates a need.

### 3.2 Release-facing source-access page (draft; not published)

This is the exact content for the download page under D2. It goes live only
after legal confirmation (L1, L2) and a separate release decision. It does not
replace `legal/SOURCE_ACCESS.md`. That file must change at the same time to
name this page.

> **Source for this release**
>
> This installer includes unmodified Qt 6.11.2, PySide6-Essentials 6.11.2 and
> shiboken6 6.11.2 under the GNU LGPL version 3. The same archives below are
> also inside the installer, in `legal/sources/`, byte for byte.
>
> | Archive | Bytes | SHA-256 | Upstream |
> | --- | --- | --- | --- |
> | `qtbase-everywhere-src-6.11.2.tar.xz` | 50,582,668 | `5b2e00eccaf5a4d8c14134ffa0ea8dfd0a35ae1ffc7f8d87fa4305a1ed23cf22` | download.qt.io archive |
> | `qtsvg-everywhere-src-6.11.2.tar.xz` | 2,341,860 | `d594337feca84c26fb67fe87b85e6a5c12fda404b611d905f9d138210c311876` | download.qt.io archive |
> | `qtimageformats-everywhere-src-6.11.2.tar.xz` | 2,050,424 | `cecd8900f34b6550076309bc94f62f828008b633a4239e0a08c86788f41001f8` | download.qt.io archive |
> | `qttranslations-everywhere-src-6.11.2.tar.xz` | 1,691,056 | `021684c1a7937a9fabc3b056a6698ad5978794caf9ac190fd6cc11399e67c014` | download.qt.io archive |
> | `pyside-setup-everywhere-src-6.11.2.tar.xz` | 18,053,248 | `cba47efbaad1bedd529725cbc14e21f156c7a19366f07b3edfbb076ffd7afdf8` | download.qt.io official_releases |
>
> Build records for the Qt binaries (official Qt build SBOMs, SPDX 2.3):
>
> | File | Bytes | SHA-256 |
> | --- | --- | --- |
> | `qtbase-6.11.2.spdx.json` | 3,863,318 | `a5c6018dd0b4096e66f697ce98b83f0ac3f8c9424720e090a1d5b00125179a24` |
> | `qtsvg-6.11.2.spdx.json` | 113,725 | `eabd595e394dfb7a9d2fd3735096fe5390377f2bee5349b02a4311ff9471e8c5` |
> | `qtimageformats-6.11.2.spdx.json` | 155,646 | `1678c477dcdf320fb04b8de1b6305278081f86b45ed72eda677fde0de9ec8b8e` |
> | `qttranslations-6.11.2.spdx.json` | 1,025,716 | `44b904f44127ce246c3fada6d759fd2759ae0dfa03375f1a413aa0c0ba2a60ee` |
>
> Also published here:
>
> - `qt-binary-provenance.json`;
> - the Social Text Intelligence source at the release tag;
> - the build receipt;
> - `SOURCE_ACCESS.md`;
> - `QT_REPLACEMENT.md`.
>
> These files stay available for as long as this installer is offered.

**Publication conditions:**

- the page sits beside the installer, or on another server with clear
  directions next to the object code (GPL v3 §6(d));
- every hash is re-checked against `distribution/source-manifest.json` and
  `distribution/qt-binary-provenance.json` at release time;
- `SOURCE_ACCESS.md` stops saying "not operational" in the same change.

## 4. Bounded owner/legal decision record

Each item is a single question. Its answer either permits one specific change or
blocks it. None is decided here. A favourable answer still needs a reviewed code
change before any blocker or `distribution_permitted` can move.

| # | Question | Blocker | If confirmed |
| --- | --- | --- | --- |
| L1 | Are the hash-pinned upstream Qt/PySide6 release sources and build scripts the Corresponding Source of the unmodified official binaries, with binding producer correspondence unproven (D1)? | B1 | B1's source question is answered |
| L2 | Is in-package delivery plus the §3.2 page adequate equivalent access (D2), and is Installation Information not triggered for download-only distribution (D3)? | B1 | The §3.2 page can be published with the release |
| L3 | Is Intel's no-reverse-engineering term, scoped in writing to the two Intel DLLs (§2), compatible with LGPLv3 §4 for the Qt libraries (D4)? | B1, B4 | D4 closes |
| L4 | Is shipping the two DLLs taken from Intel's author-signed NuGet package under the ISSL an adequate redistribution basis, given that byte-identical copies also reach the build through PyTorch under the Developer Tools EULA? | B4 | The Intel route is accepted |
| L5 | Does `NOTICE.md` (the nuspec copyright line plus the full ISSL text and third-party notices) satisfy the ISSL notice condition, given that the licence text has no copyright line? | B4 | The notice content is final |
| L6 | Does the owner accept the ISSL disclaimer, which places responsibility for use in high-risk systems on the licensee? Is the oneTBB third-party file that `third-party-programs.txt` refers to (absent from the package) needed? | B4 | B4's Intel item can close |

Outside these items, distribution also stays blocked on C15 (signing and
SmartScreen) and on the owner's release decision.

## 5. Validation

| Check | Result |
| --- | --- |
| Focused tests (`tests/tools`, licence notice) | 216 passed, 3 opt-in skipped. They cover the real pinned record, the package verifier against a synthetic package (positive; missing, size, SHA-256, SHA-512, changed, absent and duplicated entries), the build's replacement (positive; different PyTorch build, missing package, absent DLL), the packet check (NuGet copy accepted, other bytes refused) and the B4 status (a NuGet record, a PyPI-channel record and a mismatch all keep B4 open) |
| Local full suite (Windows, Python 3.12) | 1,393 passed, 7 opt-in skipped; Ruff and strict MyPy (253 files) pass |
| Private frozen build at `67ab5e9` (official CPython 3.13.16) | Exit 0; 5,364 files. `build-evidence.json` records both DLLs as taken from `intelopenmp.redist.win 2026.1.0.239`. The packet is valid, with blockers **B1** and **B4**; B4's only remaining item is the Intel legal confirmation. `legal/intel-openmp/` holds the ISSL text, the notice, the provenance record and the third-party notices, and no EULA |
| Frozen checks | `--verify-runtime`, `--smoke` (including `application_icon: true`) and `--license-info` exit 0; the opt-in frozen pytest passes 3 tests |
| Private internal installer | Compiled with Inno Setup 6.7.3: 726,685,464 bytes, SHA-256 `6a36df49ae7715a231bb8c15daec6c005bfcab449e61e24ecf657a79925a546a`; receipt checked by the harness's `Get-StiReceiptFacts` (blockers B1, B4); 5,366 payload entries, including the two DLLs and the four `legal/intel-openmp/` files. Not published |
| PR CI | One run on the final head of PR #74 |

The installer is a private validation artifact, not a release candidate for
distribution.

## 6. Not done

- No rebuild of Qt, PySide6 or PyTorch, and no change to the product
  architecture.
- No new clean-machine run: the change replaces two DLLs with byte-identical
  bytes and adds notice text, so no behavioural regression is expected and the
  S5 VMware evidence stands.
- No publication, release, signing or merge.
- No change to R2 or private evidence.
