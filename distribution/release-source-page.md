# Release source page (installer-page template)

This is the GPL v3 §6(d) equivalent-access page for B1. The owner approved this
route as D2 and assessed it as LD2 (`docs/V2_R2_LICENSE_DECISIONS.md`).

The source archives and records are **published** in the immutable GitHub
release <https://github.com/Peter-S-Shi/social-text-intelligence/releases/tag/sources-qt-6.11.2> (Release-3; `distribution/legal/SOURCE_HOSTING.json` pins its 13
assets). **The installer's download page does not exist yet.** The page content
below is the template for it: the installer release carries it, with the
`{{...}}` placeholders filled in at release time, next to the installer
download. Publishing the installer page needs its own Owner Release Gate. Filling
it in does not, on its own, permit distribution.

`tests/tools/test_m10_release_source_page.py` checks every filename and SHA-256
below against `distribution/source-manifest.json` and
`distribution/qt-binary-provenance.json`.

## Remaining release prerequisites

1. The installer's download page carries this content and links each file to the
   source release above, next to the installer download. The release stays
   available for as long as the installer is offered.
2. **Verify that same-page link** on the live page, from the public URL, before
   the release. This is the explicit final B1 prerequisite; no record states it
   done.
3. The release-facing notices already name the source release. After step 2,
   add a reviewed record of the verification and rebuild. Only that can let B1
   close; no current schema expresses it.
4. Pass the separate Owner Release Gate. Signing and SmartScreen (C15) and the
   remaining clean-machine items (C16) are outside this page.

## Page content

> **Source for Social Text Intelligence {{RELEASE_VERSION}}**
>
> The installer `{{INSTALLER_FILENAME}}` includes unmodified Qt 6.11.2,
> PySide6-Essentials 6.11.2 and shiboken6 6.11.2 under the GNU LGPL version 3.
> The same archives are inside the installer, in `legal/sources/`, byte for
> byte, and are offered here as well.
>
> | Archive | Bytes | SHA-256 |
> | --- | --- | --- |
> | `qtbase-everywhere-src-6.11.2.tar.xz` | 50,582,668 | `5b2e00eccaf5a4d8c14134ffa0ea8dfd0a35ae1ffc7f8d87fa4305a1ed23cf22` |
> | `qtsvg-everywhere-src-6.11.2.tar.xz` | 2,341,860 | `d594337feca84c26fb67fe87b85e6a5c12fda404b611d905f9d138210c311876` |
> | `qtimageformats-everywhere-src-6.11.2.tar.xz` | 2,050,424 | `cecd8900f34b6550076309bc94f62f828008b633a4239e0a08c86788f41001f8` |
> | `qttranslations-everywhere-src-6.11.2.tar.xz` | 1,691,056 | `021684c1a7937a9fabc3b056a6698ad5978794caf9ac190fd6cc11399e67c014` |
> | `pyside-setup-everywhere-src-6.11.2.tar.xz` | 18,053,248 | `cba47efbaad1bedd529725cbc14e21f156c7a19366f07b3edfbb076ffd7afdf8` |
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
> Also provided here:
>
> - `qt-binary-provenance.json`;
> - the Social Text Intelligence source at tag `{{RELEASE_TAG}}`;
> - the build receipt;
> - `SOURCE_ACCESS.md` and `QT_REPLACEMENT.md`.
>
> Source location: <https://github.com/Peter-S-Shi/social-text-intelligence/releases/tag/sources-qt-6.11.2>
>
> These files stay available for as long as this installer is offered.
