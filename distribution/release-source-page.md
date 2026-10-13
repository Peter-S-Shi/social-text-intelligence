# Release source page (prepared; not published)

This is the prepared GPL v3 §6(d) equivalent-access page for B1. The owner
approved this route as D2 and assessed it as LD2 (`docs/V2_R2_LICENSE_DECISIONS.md`).
It is **not published**. No hosting exists yet, so every `{{...}}` placeholder
stays unfilled. Publishing it is a release step that needs its own Owner Release
Gate. Filling it in does not, on its own, permit distribution.

`tests/tools/test_m10_release_source_page.py` checks every filename and SHA-256
below against `distribution/source-manifest.json` and
`distribution/qt-binary-provenance.json`.

## Publication checklist

Each item is a release step. None is done.

1. Host every file listed below at `{{SOURCE_LOCATION}}`. That is either the
   installer's download page or another server, with clear directions next to
   the installer download, kept available for as long as the installer is
   offered.
2. Re-check every hash on this page against the files actually hosted.
3. In the same change, replace the "Future source hosting" paragraph in
   `distribution/legal/SOURCE_ACCESS.md` with a pointer to this page. Then
   rebuild, so the packet and installer say where the page is.
4. Add a reviewed record that public source access is operational. Only such a
   record can let B1 close, and no current schema can express it.
5. Pass the separate Owner Release Gate. Signing and SmartScreen (C15) and the
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
> These files stay available for as long as this installer is offered.
