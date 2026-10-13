# Intel OpenMP runtime notice

`_internal/torch/lib/libiomp5md.dll` and `_internal/torch/lib/libiompstubs5md.dll`
are the Intel OpenMP runtime. They are taken unmodified from Intel's
author-signed NuGet package `intelopenmp.redist.win` version 2026.1.0.239.
`provenance.json` records the package hash and each file's hash.

Copyright Intel Corporation.

The two files are used and redistributed under the Intel Simplified Software
License (Version October 2022). The licence text is in
`INTEL-SIMPLIFIED-SOFTWARE-LICENSE.txt`. Third-party notices for the runtime are
in `third-party-programs.txt`.

## Scope of Intel's terms

Intel's terms apply **only to these two Intel files**. They forbid modifying
these files and reverse engineering, decompiling or disassembling them.

Intel's terms do not apply to anything else in this distribution:

- the Qt, PySide6 or shiboken6 libraries;
- this application;
- any other component.

They are not intended to limit the rights the GNU LGPL version 3 gives you
for the Qt libraries. Those rights include modifying the Qt libraries and reverse
engineering the combined work to debug such modifications, as described in
`QT_NOTICE.md`.

## Status

Whether this arrangement is an adequate redistribution basis still needs legal
confirmation (blocker B4). The open points are listed in `provenance.json`. Public
binary distribution is not authorized.
