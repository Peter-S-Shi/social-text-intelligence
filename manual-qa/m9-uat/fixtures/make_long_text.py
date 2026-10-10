"""Write deterministic, entirely synthetic text for a later capacity UAT step."""

from __future__ import annotations

import argparse
from pathlib import Path


def long_text() -> str:
    return " ".join(["Synthetic app feedback describes a local button."] * 160)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="A disposable local output path")
    args = parser.parse_args()
    args.output.write_text(long_text(), encoding="utf-8")


if __name__ == "__main__":
    main()
