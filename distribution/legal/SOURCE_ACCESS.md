# Source access and remaining corresponding-source obligations

This bundle includes the full Qt 6.11.2 release sources for QtBase, QtSvg,
QtImageFormats and QtTranslations, and the PySide/shiboken 6.11.2 release
source, in `sources/`. `inventory.json` records their upstream URLs and
independently checked SHA-256 values; `distribution/source-manifest.json` in the
repository is the versioned receipt. The build fails if any archive is absent or
changed, and it never downloads them. Model weights and private application data
are not included.

## Qt libraries: binaries matched to sources

`qt-sbom/` holds the official Qt 6.11.2 build SBOMs (SPDX 2.3, data license
CC0-1.0) from the Qt binary archives named in
`distribution/qt-binary-provenance.json`. During the build, every shipped Qt
library and plugin binary, and every translation file, is checked against
those SBOMs: the SHA-1 before code signing (for translations, the file's own
SHA-1) must equal the SBOM checksum. `inventory.json` records the
result under `qt_binary_provenance`.

- **QtBase and QtSvg:** each SBOM names the built Git commit
  (`qtbase@ef55f427f2c8b410d34f8a7681020a3000cf6866`,
  `qtsvg@17ca512f903f935282ebeca496aac5d11ba4199a`). The `.tag` file inside the
  delivered source archive names the same commit. The SBOM also records the
  configure command, the compiler (MSVC 19.44.35227) and CMake 3.30.5. The CI
  build instructions (`coin/`) and `configure` scripts are inside the archives.
- **QtImageFormats and QtTranslations:** each SBOM identifies the 6.11.2
  release by version only and names no commit. All 96 shipped translation
  files are byte-identical to the official release.

## PySide6 and shiboken6

The binding binaries come from the official 6.11.2 wheels. They carry no
producer build record. The delivered `pyside-setup` 6.11.2 source is the
upstream `v6.11.2` tag tree (commit
`24627cd36e1593adf22eb1f2950e4248e7bcc1ec`):

- 4,600 of its 4,602 files are identical to the tag's git blobs;
- the other two are git symlinks, stored as file copies;
- only four git housekeeping files are absent.

The source includes `build_scripts/`, `coin/` and `create_wheels.py`. It is
not proven to be the byte-exact recipe of those wheels. The shipped binding
binaries are byte-identical to the official wheels' file records. No producer
build record was found in the wheels or the materials reviewed, so exact
producer source correspondence remains unproven.

## Status

- **In this package now:** the archives in `sources/`, delivered with the object
  code.
- **Owner engineering direction.** `B1_OWNER_DECISION.json` records the
  owner's approval of decisions D1–D3 as an engineering direction:
  - keep the official, unmodified binaries with this upstream release-source
    route;
  - plan the in-package archives plus equivalent access from the download
    location;
  - keep the Qt libraries replaceable, with no signature or integrity lock.
- **Owner compliance decisions (not external legal certification).**
  `LICENSE_DECISIONS.json` records the owner's assessment of LD1–LD3:
  - LD1: these upstream release sources and build scripts are delivered as the
    Corresponding Source, with the unproven binding producer correspondence
    accepted as a residual risk;
  - LD2: in-package archives plus equivalent access are the delivery route, and
    download-only distribution does not trigger Installation Information;
  - LD3 (D4): Intel's term, scoped to its two OpenMP runtime files in
    `intel-openmp/NOTICE.md`, is compatible with LGPL v3 §4.

  B1 stays open until the installer download page links to the public
  source release below and that link is verified at release time.
- **Public source hosting (GPL v3 §6(d) equivalent access).** The same archives
  and records are publicly hosted in an immutable GitHub release:
  <https://github.com/Peter-S-Shi/social-text-intelligence/releases/tag/sources-qt-6.11.2>.
  It holds source-access materials only, no application binary. It lists
  13 assets, whose SHA-256 values `SOURCE_HOSTING.json` pins and the build
  checks against `source-manifest.json`, `qt-binary-provenance.json` and
  `QT_REPLACEMENT.md`. The release stays available for as long as any installer
  that includes these libraries is offered.
- **Not yet live: the installer download page.** The installer's download page,
  which must link to that release next to the installer, does not exist yet, and
  its same-page link has not been verified. That is a prerequisite for any
  release. This file is not a written offer.
- Installation Information is not triggered by a standalone download onto a
  user's own PC, because no User Product is transferred (LD2). No signing or
  device lock is introduced.

For rebuilding, unpack the sources in a separate workspace with a trusted
archive tool and keep their licenses. Configure QtBase with the command recorded
in its SBOM and an ABI-compatible MSVC toolchain. Build QtSvg and QtImageFormats
against that Qt, and rebuild shiboken/PySide when the binding ABI changes. See
[Qt for Python build prerequisites](https://doc.qt.io/qtforpython-6.11/shiboken6/gettingstarted.html).
Python and package license texts are provided separately. The CPython runtime
is the official Python Software Foundation 3.13.16 build
(`tags/v3.13.16:cbc944f`), checked file-by-file at build time. No Microsoft
Visual C++ runtime file is included; the installed system runtime is used.
No proprietary runtime redistribution permission is inferred from a public
download or an installed file.
