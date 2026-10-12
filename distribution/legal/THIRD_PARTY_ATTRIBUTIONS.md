# Additional frozen runtime attribution

PyInstaller 6.22.3 `_pyi_rth_utils` runtime helper:

Copyright (c) 2023, PyInstaller Development Team.

Licensed under the Apache License, Version 2.0. The full text is delivered
in the installed PyInstaller `COPYING.txt` material under `legal/packages/`;
its original filename and content hash are recorded in `legal/inventory.json`.
The same upstream text describes the distinct GPL bootloader exception and
Apache-licensed runtime hooks/fake modules.

## Rust crates compiled into tokenizers and safetensors

`legal/rust-crates/` holds the licence and copyright files of every crate in a
source superset: tokenizers 0.22.2's pinned `Cargo.lock` and safetensors 0.8.0's
CycloneDX SBOM. Each file was read from the crates.io archive verified against its
pinned SHA-256. For the two tokenizers workspace packages, the file comes from the
tokenizers repository at the `v0.22.2` commit. The vendored C++ in `esaxx-rs` has
its notices only in file headers, and those headers are included. `index.json`
maps each crate to its texts, which are stored by SHA-256.

## Intel OpenMP runtime

PyTorch ships `torch/lib/libiomp5md.dll` and `libiompstubs5md.dll`. They are
byte-identical to Intel's `intel-openmp` 2026.1.0 package. Intel's licence and
third-party notices are in `legal/intel-openmp/`, with the provenance record.
Redistribution under that licence still needs an owner/legal decision (B4).
