"""PyInstaller entry for the M7 feasibility build (experiment, not a product entry)."""

import sys

from social_text_intelligence.desktop.qt.app import main

if __name__ == "__main__":
    sys.exit(main())
