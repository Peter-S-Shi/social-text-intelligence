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

`torch/lib/libiomp5md.dll` and `libiompstubs5md.dll` are taken unmodified from
Intel's author-signed NuGet package `intelopenmp.redist.win` 2026.1.0.239, under
the Intel Simplified Software License (Version October 2022). The copies that
PyTorch's wheel brings are byte-identical; the build replaces them with the
package's copies. The licence, Intel's third-party notices, the notice and its
scope, and the provenance record are in `legal/intel-openmp/`. Whether this is
an adequate redistribution basis still needs legal confirmation (B4).
