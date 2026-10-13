"""User-facing terms for the selected Qt LGPLv3 route."""

QT_NOTICE_TITLE = "Licenses and Qt LGPL"


def qt_notice_text(qt_version: str) -> str:
    return f"""Social Text Intelligence uses Qt {qt_version}, PySide6-Essentials
and shiboken6. These libraries and their use are covered by the GNU LGPL version 3.
Qt and Qt for Python are copyright The Qt Company Ltd. and other contributors;
the accompanying notices preserve upstream copyright statements.

You may modify the LGPL libraries and replace them with interface-compatible
versions. No application term restricts reverse engineering for debugging such
modifications. The application itself remains under its separate MIT license.
Intel's terms for its two OpenMP runtime files (libiomp5md.dll and
libiompstubs5md.dll) forbid reverse engineering those two files only. They do
not apply to the Qt libraries and are not intended to limit these LGPL rights.
See intel-openmp/NOTICE.md.

The distribution's legal folder contains GNU-LGPL-3.0.txt and GNU-GPL-3.0.txt,
component license texts, a versioned inventory and preserved attribution notices.
SOURCE_ACCESS.md describes the accompanying release source archives.
QT_REPLACEMENT.md provides library replacement, build and installation instructions.
Do not replace files in a running application; use a separate copy and temporary
application data when checking compatibility.

LICENSE_DECISIONS.json records the project owner's compliance decisions and
their residual risks. They are internal assessments, not an external legal
certification. The source archives are publicly available at
https://github.com/Peter-S-Shi/social-text-intelligence/releases/tag/sources-qt-6.11.2
Public binary distribution is not authorized.
"""
