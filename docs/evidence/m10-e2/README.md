# M10-E2 public evidence receipts

- [Final build receipt](e2-build-receipt.json): layout, components, native
  owners, files that are absent by design, Qt provenance (121 verified, including
  96 translations), the official CPython runtime check, the relinked NumPy
  imports and the generated blockers.
- [Installer receipt](installer-receipt.json): the compiled per-user installer's
  hash, its runtime prerequisite check and the absence of Microsoft runtime
  files, plus the NOT RUN host and missing-runtime checks.
- [Translations comparison](translations-official-comparison.json): 96/96
  shipped `.qm` files are byte-identical to the official Qt 6.11.2 archive.
- [pyside-setup correspondence](pyside-source-correspondence.json): the delivered
  source archive compared with the upstream `v6.11.2` tag tree.
- [tokenizers crates](tokenizers-crates.json): the exact `Cargo.lock` at
  `v0.22.2`, with crates.io checksums and licence expressions.
- [Coherent replacement](replacement-e2c.json): the 6.11.1 Qt/PySide6/shiboken6
  set on the new bundle.

No binaries, SBOM documents, source archives, private logs, real project records
or machine paths are included. `distribution_permitted` is false in every
receipt. Clean-machine, formal Windows UAT, accessibility and the owner's optional
30-minute smoke remain NOT RUN.
