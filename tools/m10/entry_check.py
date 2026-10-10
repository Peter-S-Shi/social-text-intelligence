"""Console diagnostic entry; no user data is used by its smoke mode."""

from social_text_intelligence.desktop.packaged_entry import diagnostic_main

if __name__ == "__main__":
    raise SystemExit(diagnostic_main())
