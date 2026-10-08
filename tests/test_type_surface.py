"""The MyPy NumPy skip in pyproject.toml is only safe while nothing here uses NumPy."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIPPED = "numpy"


def imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_no_repository_module_imports_the_type_checker_skipped_numpy() -> None:
    users = sorted(
        str(path.relative_to(ROOT))
        for folder in ("src", "tests")
        for path in (ROOT / folder).rglob("*.py")
        if SKIPPED in imported_roots(path)
    )

    assert users == [], (
        "pyproject.toml makes MyPy skip NumPy (its 2.5+ stubs need Python 3.12 syntax, "
        "and the checker runs at python_version 3.11); code that imports it would be "
        "silently untyped. Remove the skip or type the NumPy use before adding it."
    )
