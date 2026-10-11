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

The distribution's legal folder contains GNU-LGPL-3.0.txt and GNU-GPL-3.0.txt,
component license texts, a versioned inventory and preserved attribution notices.
SOURCE_ACCESS.md describes the accompanying release source archives.
QT_REPLACEMENT.md provides library replacement, build and installation instructions.
Do not replace files in a running application; use a separate copy and temporary
application data when checking compatibility.

The engineering checks do not establish definitive legal compliance. Unresolved
source correspondence and third-party redistribution obligations are documented
in the distribution materials. Public binary distribution is not authorized.
"""
