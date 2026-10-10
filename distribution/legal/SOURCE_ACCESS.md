# Source access and remaining corresponding-source obligations

This local engineering bundle accompanies the Qt 6.11.2 release sources for
QtBase, QtSvg, QtImageFormats, QtTranslations and PySide/shiboken in `sources/`.
`inventory.json` records upstream URLs and independently checked SHA-256 values.
The repository's `distribution/source-manifest.json` is the versioned receipt.
These are full upstream release archives, not snippets or a link-only offer.
The build fails if any required archive is absent or changed. Build preparation
must acquire these exact public upstream files separately; the build never
downloads them. Model weights and private application data are not included.

This is **not a written offer** and creates no unsupported promise of a future
source service. It is also not yet a complete corresponding-source claim:
upstream releases do not prove the wheel's precise build configuration, patches,
software-renderer sources or static dependency link units. Before distribution,
resolve those differences, deliver all required matching source/build materials
alongside the binary, and check the chosen LGPL/GPL conveyance route against its
actual terms. Installation Information, if required by the applicable route and
product classification, must also be supplied. No signing or device lock is
introduced here.

For rebuilding, unpack the sources in a separate workspace using a trusted
archive tool, retain their licenses, and follow the included QtBase build
instructions and PySide setup README. Build Windows x64 shared Qt libraries
with an ABI-compatible MSVC toolchain; build QtSvg/QtImageFormats against that
same Qt build and use the matching shiboken/PySide build when wrapper ABI changes
require it. The PySide build prerequisites include its supported Python, CMake,
Ninja and libclang versions. The exact producer flags and dependency sources
remain blocker B1; these high-level steps are not represented as a reproduced
upstream build recipe. See [Qt for Python build prerequisites](https://doc.qt.io/qtforpython-6.11/shiboken6/gettingstarted.html).

Python and package license texts are provided separately. Package-level notices
and source-superset Qt acknowledgments must not be mistaken for a certified
compiled-content SBOM. No proprietary runtime redistribution permission is
inferred from a public download or an installed file.
