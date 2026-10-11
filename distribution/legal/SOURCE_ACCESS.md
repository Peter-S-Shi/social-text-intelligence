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
library and plugin binary is checked against those SBOMs: the binary's SHA-1
before code signing must equal the SBOM checksum. `inventory.json` records the
result under `qt_binary_provenance`.

- **QtBase and QtSvg:** each SBOM names the built Git commit
  (`qtbase@ef55f427f2c8b410d34f8a7681020a3000cf6866`,
  `qtsvg@17ca512f903f935282ebeca496aac5d11ba4199a`). The `.tag` file inside the
  delivered source archive names the same commit. The SBOM also records the
  configure command, the compiler (MSVC 19.44.35227) and CMake 3.30.5. The CI
  build instructions (`coin/`) and `configure` scripts are inside the archives.
- **QtImageFormats:** the SBOM identifies the 6.11.2 release by version only
  and names no commit.
- **Not covered:** the Qt-licensed translation data files.

## PySide6 and shiboken6

The binding binaries come from the official 6.11.2 wheels. They carry no
producer build record. The delivered `pyside-setup` 6.11.2 source includes its
`build_scripts/`, `coin/` and `create_wheels.py`; it is not proven to be the
byte-exact recipe of those wheels.

## Status

This is **not a written offer**. It is also not yet a complete legal clearance.
The proposed release route places these same source archives next to the
installer on the same download page. The owner (and legal review, where
needed) must confirm that route, the binding-source position, and whether
Installation Information applies. No signing or device lock is introduced.

For rebuilding, unpack the sources in a separate workspace with a trusted
archive tool and keep their licenses. Configure QtBase with the command recorded
in its SBOM and an ABI-compatible MSVC toolchain. Build QtSvg and QtImageFormats
against that Qt, and rebuild shiboken/PySide when the binding ABI changes. See
[Qt for Python build prerequisites](https://doc.qt.io/qtforpython-6.11/shiboken6/gettingstarted.html).
Python and package license texts are provided separately. No proprietary
runtime redistribution permission is inferred from a public download or an
installed file.
