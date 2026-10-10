# M10-B public evidence receipts

- [Inventory receipt](inventory-receipt.json): actual Windows frozen-file and
  installed-license audit, exact source/tool identities, package notice hashes,
  native hashes, source receipts and structural verification result.
- [Replacement evidence](replacement-evidence.json): independently sourced
  upstream wheels, changed DLL/plugin hashes and both observed failed checks.

The complete 1,513,576-byte `legal/inventory.json` accompanies the local artifact;
its SHA-256 is recorded here. The public receipt omits the 6,648-module list and
full 5,264-file manifest while preserving counts, native/package detail and the
full inventory identity. The 224-entry Qt source-notice superset is summarized
as 190 unique files; it is not a compiled-content SBOM.

No binaries, full source archives, private logs, real project records or machine
paths are included. These receipts record engineering verification; B1–B6
remain unresolved, distribution is blocked, and formal Windows UAT, accessibility
acceptance and the owner's optional 30-minute smoke are NOT RUN.
