"""Invented demo feedback for the local demo launcher (not real people or posts)."""

from __future__ import annotations

HEADER = "text,language,timestamp,topic,community"

ROWS = (
    (
        "The new dashboard is a huge step up, I found everything in seconds.",
        "en",
        "2026-03-02T09:15:00Z",
        "dashboard",
        "beta-testers",
    ),
    (
        "Export keeps timing out and I lost an hour of work. Really frustrating.",
        "en",
        "2026-03-02T10:40:00Z",
        "export",
        "beta-testers",
    ),
    (
        "The release notes were clear and the upgrade went smoothly.",
        "en",
        "2026-03-03T08:05:00Z",
        "upgrade",
        "newsletter",
    ),
    (
        "I am not sure what the new filter button actually does.",
        "en",
        "2026-03-03T11:20:00Z",
        "dashboard",
        "newsletter",
    ),
    (
        "Support answered within ten minutes. Thank you, that was lovely.",
        "en",
        "2026-03-04T14:00:00Z",
        "support",
        "beta-testers",
    ),
    (
        "The mobile layout is cramped and the text is hard to read.",
        "en",
        "2026-03-04T16:30:00Z",
        "mobile",
        "forum",
    ),
    (
        "Meeting moved to Thursday at noon, please update your calendars.",
        "en",
        "2026-03-05T07:45:00Z",
        "upgrade",
        "newsletter",
    ),
    (
        "Honestly worried the next update will break my saved views again.",
        "en",
        "2026-03-05T12:10:00Z",
        "dashboard",
        "forum",
    ),
    (
        "Dark mode looks fantastic, the team clearly cared about the details.",
        "en",
        "2026-03-06T09:00:00Z",
        "dashboard",
        "beta-testers",
    ),
    (
        "Why does every import ask me to pick the column again? Annoying.",
        "en",
        "2026-03-06T13:25:00Z",
        "import",
        "forum",
    ),
    (
        "The tutorial video was helpful and short, exactly what I needed.",
        "en",
        "2026-03-07T10:10:00Z",
        "support",
        "newsletter",
    ),
    (
        "Pricing page is confusing and I could not find the student plan.",
        "en",
        "2026-03-07T15:50:00Z",
        "pricing",
        "forum",
    ),
    (
        "Just wanted to say the weekly digest made my Monday better.",
        "en",
        "2026-03-08T08:30:00Z",
        "newsletter",
        "newsletter",
    ),
    (
        "The search results feel random lately, I expected better than this.",
        "en",
        "2026-03-08T17:05:00Z",
        "search",
        "beta-testers",
    ),
    (
        "Installed on the second laptop without any trouble at all.",
        "en",
        "2026-03-09T09:40:00Z",
        "upgrade",
        "beta-testers",
    ),
    (
        "Not thrilled about the new limit on exports, but I understand why.",
        "en",
        "2026-03-09T11:55:00Z",
        "export",
        "forum",
    ),
    (
        "Merci pour la mise a jour, tout fonctionne tres bien chez moi.",
        "fr",
        "2026-03-10T10:00:00Z",
        "upgrade",
        "forum",
    ),
    (
        "lol the loading animation is weirdly satisfying",
        "en",
        "2026-03-10T14:20:00Z",
        "dashboard",
        "forum",
    ),
    ("", "en", "2026-03-11T09:00:00Z", "search", "forum"),
    (
        "Third crash this week on startup. I am close to giving up on this tool.",
        "en",
        "2026-03-11T18:15:00Z",
        "upgrade",
        "beta-testers",
    ),
)


def csv_text() -> str:
    lines = [HEADER]
    for text, language, stamp, topic, community in ROWS:
        quoted = '"' + text.replace('"', '""') + '"' if text else ""
        lines.append(f"{quoted},{language},{stamp},{topic},{community}")
    return "\n".join(lines) + "\n"
