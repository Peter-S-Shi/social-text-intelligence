# V2 M10 S4 — B1 source-delivery decision memo

Status: **decision memo for the owner; B1 stays OPEN.** This is a read-only
review from `main@bf044be9`. No release asset, compliance code, binding rebuild
or publication was made. It is an engineering reading of the licences, not legal
advice. Other states are unchanged: B4 OPEN; B6 closed only on its narrow
QtCore criterion; S5 NOT RUN; `distribution_permitted` false.

## 1. Question

The installer ships unmodified official Qt 6.11.2 libraries and unmodified
official PySide6-Essentials/shiboken6 6.11.2 binding binaries. Does delivering
the hash-pinned upstream release sources and build scripts satisfy the source
obligations? Or does STI need to rebuild the bindings itself?

## 2. What is verified

| Item | Evidence | Strength |
| --- | --- | --- |
| Qt libraries and plugins (25) and translations (96) | Every file matches the official Qt 6.11.2 build SBOMs (M10-E2 §2.3). QtBase and QtSvg are linked **by commit**: the SBOM's built commit equals the delivered archive's `.tag`. QtImageFormats and QtTranslations are linked **by version only** | producer record: yes |
| Binding binaries (7: `QtCore/QtGui/QtNetwork/QtWidgets.pyd`, `pyside6.abi3.dll`, `Shiboken.pyd`, `shiboken6.abi3.dll`) | **S4 check:** all 32 native files under `PySide6/` and `shiboken6/` in the frozen bundle are byte-identical to the RECORD hashes of the installed official `pyside6_essentials-6.11.2` and `shiboken6-6.11.2` wheels | unmodified: yes |
| Binding build provenance | The wheels' `_config.py` records version 6.11.2 and build date 2026-08-14. The git-commit fields are **empty**, and no build SBOM is shipped | **producer record: no** |
| Binding source | The delivered `pyside-setup-everywhere-src-6.11.2.tar.xz`, from Qt's official release directory, equals the upstream `v6.11.2` tag tree (`24627cd…`): 4,600 of 4,602 files identical, and the other two are symlink copies. It contains `build_scripts/`, `coin/` and `create_wheels.py` (M10-E2 §2.3) | version correspondence: yes |
| Replacement | Separately obtained official 6.11.2 Qt: PASS. Coherent 6.11.1 Qt/PySide6/shiboken6 set: PASS. Modified-source QtCore: PASS (S3, QtCore only). A Qt-only swap to another version fails on Qt's version-tagged private API, which `QT_REPLACEMENT.md` documents | dynamic replacement: shown |
| STI terms | MIT. `QT_NOTICE.md` permits modification and reverse engineering for debugging. There is no signature check or replacement lock | no restriction |

The missing item is narrow. Nothing shows the exact recipe that produced the
official binding wheels. Source **version** correspondence is verified; the
**producer build record** is absent. Qt does not publish one for these wheels.

## 3. Obligations (engineering reading)

- **The Combined Work, LGPL v3 §4.**
  - (a) notice and (b) licence texts: shipped.
  - (c) display in the app: the licence dialog.
  - (d)(1) a suitable shared-library mechanism: Qt and the bindings are separate,
    replaceable files, shown in §2.
  - (e) Installation Information: see §5.
- **The libraries' own object code, through GPL v3 §6 as incorporated by the
  LGPL.** "Corresponding Source" means the source needed to generate, install
  and run the object code, including the scripts that control those activities.
  - For the Qt libraries, the delivered sources are tied to the binaries by
    the SBOM commit or version.
  - For the bindings, the publisher's own release source and build scripts are
    delivered, and STI changed nothing.
  - On its face, GPL v3 does not require a reproducible build or a producer log.
    Whether matching-version upstream source *without* a producer record counts
    as the Corresponding Source of those exact binaries is **the one genuinely
    legal question** in B1.
- **What a binding rebuild would and would not do.**
  - It **would** let STI ship binaries with a known exact recipe.
  - It would **not** create provenance for the official binaries. It replaces
    them with STI-built, unsigned ones, which makes STI their producer, with
    full build and testing responsibility.
  - It needs a full Qt development install and libclang, and hours of build time.
  - It does **not** affect the Qt libraries, whose position is the same either
    way.

## 4. Proposed delivery arrangement (proposal only; nothing is published)

1. **In the package (already in place).** The installer payload carries
   `legal/sources/`: the five pinned archives from
   `distribution/source-manifest.json`. It also carries `qt-sbom/`,
   `inventory.json` with the SHA-256 values, and the notices. The source therefore
   travels in the same download as the object code.
2. **On the same download page (future release).** Under the installer, a
   "Source for this release" section with:
   - the same five archives, by file name, size and SHA-256 (byte-identical to
     `legal/sources/`);
   - the four Qt build SBOMs and `qt-binary-provenance.json`;
   - the STI source at the release tag and the build receipt;
   - `SOURCE_ACCESS.md`.

   They must be hosted on the same host and stay available for as long as the
   installer is offered (GPL v3 §6(d)).
3. **Notice changes at release.** `SOURCE_ACCESS.md` currently says the route is
   "proposed" and that it is "not a written offer". It should name the page and
   say the archives there equal the in-package copies. No written offer is needed
   when the source accompanies the download and sits beside it.

## 5. Installation Information and reverse engineering

- **Installation Information** (GPL v3 §6, LGPL v3 §4(e)) applies only to object
  code conveyed in or with a "User Product" as part of transferring the device.
  STI is software that users download onto their own general-purpose PC.
  - On this reading it is **not triggered**.
  - Even if it were, the substance is met. Installation is a file copy described
    in `QT_REPLACEMENT.md`, and an unsigned modified `Qt6Core.dll` runs (S3).
  - **Condition to keep:** any future code signing (the S5 SmartScreen decision)
    may sign the executables and the installer, but must not add a signature or
    integrity check on the Qt/PySide6 files.
  - This is not a separate blocker. Owner/legal should confirm it is not
    applicable as part of the B1 decision.
- **Reverse engineering.** STI imposes no restriction, and `QT_NOTICE.md`
  expressly permits it. A **separate unresolved condition** comes from B4:
  - Intel's EULA §2.1.D(2) would require STI's end-user terms to prohibit reverse
    engineering of the Intel OpenMP DLLs.
  - LGPL v3 §4 requires terms that do not restrict reverse engineering for
    debugging modifications of the Qt portions of the Combined Work.
  - A term limited to Intel's files may be compatible, but that is a legal
    question. It links B1 and B4 and must be decided with B4. It does not affect
    the B1 source question.

## 6. Recommendation

**The existing upstream-source route is sufficient for owner/legal acceptance.
A binding rebuild is not genuinely necessary.** The reasons:

- The shipped binaries are the publisher's unmodified wheels, verified byte for
  byte.
- The publisher's own release source and build scripts are delivered, verified
  against the tag.
- Replacement has been shown.
- A rebuild would swap provenance rather than add it.

A rebuild is warranted only if counsel holds that Corresponding Source requires a
producer-verified recipe. Even then, the minimal step is rebuilding the seven
binding binaries, not Qt.

## 7. Decisions requested, and the smallest route forward

| # | Decision | Recommended answer |
| --- | --- | --- |
| D1 | Accept the hash-pinned `pyside-setup` 6.11.2 release source and build scripts as the Corresponding Source of the unmodified official binding binaries, and accept the commit-linked/version-linked Qt sources for the Qt binaries | accept |
| D2 | Delivery: in-package sources plus the same-page assets in §4 | accept |
| D3 | Installation Information is not applicable; keep the no-lock condition in §5 | confirm |
| D4 | Whether an Intel-only anti-reverse-engineering term is compatible with LGPL §4 (decided jointly with B4) | legal review |

After D1–D3, engineering would, in a separate approved milestone:

1. record the position in a versioned file that the packet reads, so that
   `compliance.py` stops deriving B1 only while that record is present (fails
   closed);
2. refresh the stale shipped notices: `QT_REPLACEMENT.md` and `QT_NOTICE.md`
   still say a modified-source replacement is not demonstrated, the
   `INSTALLER_NOTICE.txt` blocker list is stale, and `installer.py` has a fixed
   `legal_blockers` list;
3. prepare the release-page assets only when a release is authorized.

Until then, B1 stays OPEN.
