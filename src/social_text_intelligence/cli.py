"""Dependency-free command-line diagnostics for the local project."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from . import __version__
from .foundation import PROJECT_STATUS


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser without accessing user data or the network."""

    parser = argparse.ArgumentParser(
        prog="sti",
        description="Local diagnostics for the Social Text Intelligence project.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("about", help="Show the current project milestone.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the local diagnostic command."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    print(PROJECT_STATUS.name)
    print(f"Milestone: {PROJECT_STATUS.milestone}")
    print("Local-first: yes")
    print("Analysis contracts available: no")
    print("Model inference available: no")
    return 0
