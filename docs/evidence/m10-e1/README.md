# M10-E1 public evidence receipts

- [Replacement evidence](replacement-evidence.json): import-gap analysis
  explaining the M10-B failures, and the E3/E2 experiments (M10-B bundle) and
  E3b/E2b experiments (M10-E1 bundle). Each records its replacement sources,
  every changed file hash and its observed checks.
- [Qt provenance, M10-B bundle](qt-provenance-m10b-bundle.json): wheel vs
  official binary content comparison, and the SBOM verification of the
  previously built bundle.
- [M10-E1 build receipt](e1-build-receipt.json): the actual build's layout,
  staged SBOM hashes, Qt provenance result, preserved wheel SBOMs and the
  generated blockers.
- [Packet correction receipt](e1-packet-correction-receipt.json): the
  pre-merge fix restoring PySide6-Essentials/shiboken6 to the component
  audit, regenerated over the same actual bundle.
- [Compiled Rust crates](rust-compiled-crates.json): crate@version lower bounds
  recovered from the three Rust extensions.

No binaries, SBOM documents, source archives, private logs, real project records
or machine paths are included. These receipts are engineering verification
only; `distribution_permitted` is false in all of them. Clean-machine checks,
formal Windows UAT, accessibility acceptance and the owner's optional 30-minute
smoke remain NOT RUN.
