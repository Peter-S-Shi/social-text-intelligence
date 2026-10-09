"""Synthetic data and providers for the visual-evidence run only.

Nothing here is real or private text: the sentences are invented product feedback.
The providers are *not* models; they turn keywords into varied, plausible-looking
scores so that every screen can be drawn with bars of different lengths, secondary
emotions, threshold fallbacks, and disagreements. They never support an accuracy
claim of any kind.
"""

from __future__ import annotations

import hashlib

from social_text_intelligence.contracts import (
    EmotionLabel,
    EmotionResult,
    EmotionScore,
    NativeScore,
    NormalizedTextInput,
    ProviderMetadata,
    SentimentLabel,
    SentimentResult,
    SentimentScore,
    TaskType,
)
from social_text_intelligence.contracts.errors import ProviderError

FAIL_MARKER = "FAILME"
GO_EMOTIONS = [
    "admiration",
    "amusement",
    "anger",
    "annoyance",
    "approval",
    "caring",
    "confusion",
    "curiosity",
    "desire",
    "disappointment",
    "disapproval",
    "disgust",
    "embarrassment",
    "excitement",
    "fear",
    "gratitude",
    "grief",
    "joy",
    "love",
    "nervousness",
    "optimism",
    "pride",
    "realization",
    "relief",
    "remorse",
    "sadness",
    "surprise",
    "neutral",
]
assert len(GO_EMOTIONS) == 28

POSITIVE = (
    "love",
    "great",
    "thanks",
    "thank you",
    "fixed",
    "helpful",
    "smooth",
    "clear",
    "brilliant",
    "happy",
    "works fine",
)
NEGATIVE = (
    "crash",
    "charged twice",
    "broken",
    "stuck",
    "slow",
    "refund",
    "disappointed",
    "furious",
    "angry",
    "can't",
    "cannot",
    "worried",
    "lost",
)
EMOTION_KEYWORDS = (
    (EmotionLabel.GRATITUDE, ("thanks", "thank you")),
    (EmotionLabel.ANGER, ("furious", "angry", "charged twice")),
    (EmotionLabel.SADNESS, ("disappointed", "lost")),
    (EmotionLabel.FEAR, ("worried",)),
    (EmotionLabel.ADMIRATION, ("brilliant", "clear")),
    (EmotionLabel.AMUSEMENT, ("lol", "funny")),
    (EmotionLabel.JOY, ("love", "great", "happy", "fixed", "smooth")),
    (EmotionLabel.DISGUST, ("awful", "terrible")),
)

SENTIMENT_META = ProviderMetadata(
    provider="visual-evidence",
    model_name="synthetic-sentiment",
    revision="synthetic-1",
    task=TaskType.SENTIMENT,
    supported_languages=("en",),
    native_labels=("negative", "neutral", "positive"),
)
EMOTION_META = ProviderMetadata(
    provider="visual-evidence",
    model_name="synthetic-emotion",
    revision="synthetic-1",
    task=TaskType.EMOTION,
    supported_languages=("en",),
    native_labels=tuple(GO_EMOTIONS),
)


def _unit(text: str, salt: str) -> float:
    digest = hashlib.sha256(f"{salt}|{text}".encode()).digest()
    return int.from_bytes(digest[:4], "big") / 0xFFFFFFFF


def _has(text: str, words: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in words)


class SyntheticSentiment:
    metadata = SENTIMENT_META

    def validate_input(self, record: NormalizedTextInput) -> None:
        return None

    def analyze(self, record: NormalizedTextInput) -> SentimentResult:
        if FAIL_MARKER in record.text:
            raise ProviderError(
                provider="synthetic",
                code="model_error",
                message="The model could not score this row.",
            )
        good, bad = _has(record.text, POSITIVE), _has(record.text, NEGATIVE)
        if bad and not good:
            label = SentimentLabel.NEGATIVE
        elif good and not bad:
            label = SentimentLabel.POSITIVE
        elif good and bad:
            label = (
                SentimentLabel.NEGATIVE
                if _unit(record.text, "mix") < 0.55
                else SentimentLabel.POSITIVE
            )
        else:
            label = SentimentLabel.NEUTRAL
        top = 0.52 + 0.45 * _unit(record.text, "top")
        rest = 1.0 - top
        split = _unit(record.text, "split")
        scores = {}
        others = [item for item in SentimentLabel if item is not label]
        scores[label] = top
        scores[others[0]] = rest * split
        scores[others[1]] = rest * (1 - split)
        ordered = tuple(SentimentScore(item, scores[item]) for item in SentimentLabel)
        return SentimentResult(
            record_id=record.record_id,
            label=label,
            confidence=top,
            scores=ordered,
            native_scores=tuple(
                NativeScore(name, scores[SentimentLabel(name)])
                for name in SENTIMENT_META.native_labels
            ),
            provider=SENTIMENT_META,
        )


class SyntheticEmotion:
    metadata = EMOTION_META
    threshold = 0.5

    def validate_input(self, record: NormalizedTextInput) -> None:
        return None

    def analyze(self, record: NormalizedTextInput) -> EmotionResult:
        text = record.text
        base = {label: 0.02 + 0.2 * _unit(text, label.value) for label in EmotionLabel}
        active = [label for label, words in EMOTION_KEYWORDS if _has(text, words)][:2]
        for rank, label in enumerate(active):
            base[label] = (0.88 - 0.06 * rank) * (0.8 + 0.2 * _unit(text, "lift"))
        if not active:
            base[EmotionLabel.NEUTRAL] = 0.45 + 0.35 * _unit(text, "neutral")
        else:
            base[EmotionLabel.NEUTRAL] = 0.1 + 0.25 * _unit(text, "n2")
        qualified = sorted(
            (
                label
                for label in EmotionLabel
                if label is not EmotionLabel.NEUTRAL and base[label] >= self.threshold
            ),
            key=lambda label: (-base[label], label.value),
        )
        dominant = qualified[0] if qualified else EmotionLabel.NEUTRAL
        secondary = tuple(qualified[1:])
        native_total = 0.0
        native: dict[str, float] = {}
        for name in GO_EMOTIONS:
            mapped = {
                "joy": EmotionLabel.JOY,
                "amusement": EmotionLabel.AMUSEMENT,
                "admiration": EmotionLabel.ADMIRATION,
                "gratitude": EmotionLabel.GRATITUDE,
                "anger": EmotionLabel.ANGER,
                "sadness": EmotionLabel.SADNESS,
                "fear": EmotionLabel.FEAR,
                "disgust": EmotionLabel.DISGUST,
                "neutral": EmotionLabel.NEUTRAL,
            }.get(name)
            value = base[mapped] if mapped else 0.01 + 0.18 * _unit(text, name)
            native[name] = min(value, 1.0)
            native_total += value
        return EmotionResult(
            record_id=record.record_id,
            dominant_emotion=dominant,
            confidence=base[dominant],
            threshold=self.threshold,
            secondary_emotions=secondary,
            scores=tuple(EmotionScore(label, base[label]) for label in EmotionLabel),
            native_scores=tuple(
                NativeScore(name, native[name]) for name in GO_EMOTIONS
            ),
            provider=EMOTION_META,
        )


SENTENCES = (
    "The new update fixed the login bug, thanks a lot to the team.",
    "I was charged twice this month and I am furious. Please refund the duplicate.",
    "Export to CSV works fine for me.",
    "The tutorial was clear and the sample project helped a lot.",
    "Sync has been stuck on pending since yesterday and I am worried about my data.",
    "Brilliant release, the search is so much faster now.",
    "Dark mode looks lovely, but the battery drain is not.",
    "I love how smooth the import is, great work.",
    "The app crashes whenever I open the export dialog. Really disappointed.",
    "Fine.",
    "It is a table of numbers with a column for dates.",
    "Support answered quickly and the fix worked, thank you so much.",
    "Pricing page is confusing and I cannot find where to cancel.",
    "lol the loading spinner is funny but please make it stop spinning forever",
    "Happy with the new filters, they save me a lot of time.",
    "I lost two hours of notes after the last update. Awful.",
    "The documentation covers everything I needed for the setup.",
    "Why is the settings screen so slow on my laptop?",
    "Great onboarding, the checklist made the first day easy.",
    "The invoice export is broken again and nobody replied to my ticket.",
    "Okay, nothing special about the new layout.",
    "Thanks for adding keyboard shortcuts, it feels so much better.",
    "The refund took three weeks and I am angry about how it was handled.",
    "The report totals match my spreadsheet, which is a relief.",
    "I can't sign in after resetting my password, it keeps looping.",
    "Really helpful release notes this time.",
    "The mobile view is cramped and the buttons are tiny.",
    "Love the charts. Hate that I cannot export them as images.",
)


def feedback_csv() -> bytes:
    """About 50 rows with every kind of problem a project can have.

    Rejected at import: a duplicate id (two rows), an empty text, a bad timestamp.
    Fails in analysis: the row carrying the failure marker.
    Language: supplied tags and detected languages disagree on purpose.
    """

    header = (
        "record_id,text,source_type,source_label,language,timestamp,topic,community"
    )
    rows: list[str] = [header]
    topics = ("billing", "login", "export", "sync", "")
    communities = ("north", "south", "west")

    def add(rid: str, text: str, language: str = "en", topic: str = "") -> None:
        n = len(rows)
        month = 1 + n % 3
        day = 1 + n % 27
        stamp = f"2026-{month:02d}-{day:02d}T10:00:00Z"
        safe = text.replace('"', "'")
        rows.append(
            f'{rid},"{safe}",file,Autumn survey,{language},{stamp},'
            f"{topic or topics[n % len(topics)]},{communities[n % len(communities)]}"
        )

    for index in range(38):
        add(f"c-{1001 + index}", SENTENCES[index % len(SENTENCES)])
    add("c-2001", "Merci beaucoup, la nouvelle version est beaucoup plus rapide.")
    add(
        "c-2002",
        "Das Update hat das Problem leider nicht gelöst und ich bin enttäuscht.",
    )
    add("c-2003", "Gracias, el equipo respondió muy rápido y todo funciona bien.", "es")
    add("c-2004", "ok")
    add("c-2005", "👍👍👍")
    add("c-2006", "https://example.com/help/article/4821?ref=survey")
    add("c-3001", "Thanks, this one is a duplicate id on purpose.")
    add("c-3001", "Great, and so is this one.")
    add("c-3002", "")
    rows.append(
        'c-3003,"A row with a broken timestamp.",file,Autumn survey,en,not-a-date,'
        "billing,north"
    )
    add("c-4001", f"This row will fail inside the model: {FAIL_MARKER}.")
    add("c-4002", "Final check: everything arrived on time and works fine.")
    return ("\n".join(rows) + "\n").encode("utf-8")


def checkout_csv() -> bytes:
    """48 data rows shaped like the Round 3 reference project.

    One empty text (rejected at import), one row the synthetic model fails on, one
    French row, and three ``source_label`` groups for the Insights comparison.
    """

    header = "record_id,text,source_label,topic,timestamp"
    sources = ("app_store", "support", "forum")
    topics = ("pricing", "performance", "login", "export")
    rows = [header]
    for index in range(46):
        text = SENTENCES[index % len(SENTENCES)].replace('"', "'")
        if index == 7:
            text = "Merci, la nouvelle version est beaucoup plus rapide."
        rows.append(
            f'c-{1001 + index},"{text}",{sources[index % 3]},{topics[index % 4]},'
            f"2026-{1 + index % 3:02d}-{1 + index % 27:02d}T09:00:00Z"
        )
    rows.append("c-1047,,support,login,2026-02-03T09:00:00Z")
    rows.append(
        f'c-1048,"This row will fail inside the model: {FAIL_MARKER}.",forum,export,'
        "2026-02-04T09:00:00Z"
    )
    return ("\n".join(rows) + "\n").encode("utf-8")


def support_inbox_csv() -> bytes:
    """14 rows with an unconventionally named text column, one empty, one Spanish."""

    texts = (
        "Billing page shows the wrong currency after the update.",
        "Great job on the new search, it's instant now.",
        "Can I export only the reviewed rows?",
        "The reminder feature woke me at 3am. Twice.",
        "Gracias por la ayuda, todo funciona.",
        "Not impressed, it's the same app with a new logo.",
        "Agent was patient and walked me through the restore. Thank you!",
        "I can't tell if the backup ran or not.",
        "",
        "Seriously the best note app on Windows right now.",
        "My team keeps getting duplicate notifications.",
        "Loving the calendar integration, small but mighty.",
        "[3,410-character log pasted into the feedback form]",
        "Why is the student plan hidden?",
    )
    kinds = ("support", "app_store", "forum")
    rows = ["record_id,message_body,source_label,topic,timestamp"]
    for index, text in enumerate(texts):
        body = f'"{text}"' if text else ""
        rows.append(
            f"o-{1001 + index},{body},{kinds[index % 3]},billing,"
            f"2026-10-{1 + index:02d}T09:00:00Z"
        )
    return ("\n".join(rows) + "\n").encode("utf-8")
