"""Dependency-free command-line diagnostics for the local project."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .contracts.errors import SocialTextIntelligenceError
from .contracts.inputs import NormalizedTextInput
from .contracts.results import EmotionLabel, SentimentLabel
from .foundation import PROJECT_STATUS
from .providers.cardiff_sentiment import CardiffSentimentProvider
from .providers.samlowe_emotion import (
    DEFAULT_EMOTION_THRESHOLD,
    SamLoweEmotionProvider,
)
from .services.analysis import AnalysisService, SentimentAnalysisService


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser without accessing user data or the network."""

    parser = argparse.ArgumentParser(
        prog="sti",
        description="Local diagnostics for the Social Text Intelligence project.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("about", help="Show the current project milestone.")
    subparsers.add_parser("contracts", help="Show normalized analysis labels.")
    sentiment = subparsers.add_parser(
        "sentiment",
        help="Analyze one English text with the licensed local sentiment model.",
    )
    sentiment.add_argument("text", help="One text to analyze locally.")
    sentiment.add_argument("--language", default="en", help="BCP 47 language tag.")
    sentiment.add_argument(
        "--cache-dir",
        default="model_cache",
        help="Ignored directory used for downloaded model files.",
    )
    sentiment.add_argument(
        "--offline",
        action="store_true",
        help="Require the pinned model revision to already exist in the cache.",
    )
    analyze = subparsers.add_parser(
        "analyze",
        help="Analyze sentiment and compact emotions for one English text locally.",
    )
    analyze.add_argument("text", help="One text to analyze locally.")
    analyze.add_argument("--language", default="en", help="BCP 47 language tag.")
    analyze.add_argument(
        "--cache-dir",
        default="model_cache",
        help="Ignored directory used for downloaded model files.",
    )
    analyze.add_argument(
        "--offline",
        action="store_true",
        help="Require both pinned model revisions to exist in the local cache.",
    )
    analyze.add_argument(
        "--emotion-threshold",
        type=float,
        default=DEFAULT_EMOTION_THRESHOLD,
        help="Inclusive threshold for compact non-neutral emotions (default: 0.5).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the local diagnostic command."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "contracts":
        print("Sentiment labels: " + ", ".join(SentimentLabel))
        print("Emotion labels: " + ", ".join(EmotionLabel))
        print("Sentiment provider: licensed local model available")
        print("Emotion provider: licensed local multi-label model available")
        return 0

    if args.command == "sentiment":
        try:
            record = NormalizedTextInput.from_text(
                args.text,
                language=args.language,
            )
            service = SentimentAnalysisService(
                CardiffSentimentProvider(
                    cache_dir=Path(args.cache_dir),
                    offline=args.offline,
                )
            )
            result = service.analyze(record)
        except SocialTextIntelligenceError as error:
            parser.error(str(error))
        print(f"Sentiment: {result.label}")
        print(f"Confidence: {result.confidence:.6f}")
        print(
            "Scores: "
            + ", ".join(f"{item.label}={item.score:.6f}" for item in result.scores)
        )
        print(f"Model: {result.provider.model_name}")
        print(f"Revision: {result.provider.revision}")
        print("Estimate only: review context before relying on this prediction.")
        return 0

    if args.command == "analyze":
        try:
            record = NormalizedTextInput.from_text(
                args.text,
                language=args.language,
            )
            cache_dir = Path(args.cache_dir)
            analysis_service = AnalysisService(
                sentiment_provider=CardiffSentimentProvider(
                    cache_dir=cache_dir,
                    offline=args.offline,
                ),
                emotion_provider=SamLoweEmotionProvider(
                    threshold=args.emotion_threshold,
                    cache_dir=cache_dir,
                    offline=args.offline,
                ),
            )
            analysis_report = analysis_service.analyze(record)
        except SocialTextIntelligenceError as error:
            parser.error(str(error))

        sentiment = analysis_report.sentiment
        emotion = analysis_report.emotion
        emotion_scores = {item.label: item.score for item in emotion.scores}
        native_active = tuple(
            item for item in emotion.native_scores if item.score >= emotion.threshold
        )
        print(f"Sentiment: {sentiment.label}")
        print(f"Sentiment confidence: {sentiment.confidence:.6f}")
        print(f"Dominant emotion: {emotion.dominant_emotion}")
        print(f"Emotion confidence: {emotion.confidence:.6f}")
        print(f"Emotion threshold: {emotion.threshold:.6f} (inclusive)")
        print(
            "Secondary emotions: "
            + (
                ", ".join(
                    f"{label}={emotion_scores[label]:.6f}"
                    for label in emotion.secondary_emotions
                )
                or "none"
            )
        )
        print(
            "Compact emotion scores: "
            + ", ".join(
                f"{item.label}={item.score:.6f}" for item in emotion.scores
            )
        )
        print(
            "Native emotions at/above threshold: "
            + (
                ", ".join(f"{item.label}={item.score:.6f}" for item in native_active)
                or "none"
            )
        )
        print(
            "Models: "
            f"sentiment={sentiment.provider.model_name}@{sentiment.provider.revision}; "
            f"emotion={emotion.provider.model_name}@{emotion.provider.revision}"
        )
        print(
            "Estimates only: emotions are not psychological diagnoses; review context."
        )
        return 0

    print(PROJECT_STATUS.name)
    print(f"Milestone: {PROJECT_STATUS.milestone}")
    print("Local-first: yes")
    print("Analysis contracts available: yes")
    print("Local sentiment inference available: yes")
    print("Local emotion inference available: yes")
    print("Combined single-text report available: yes")
    print("Local Flask interface available: yes")
    print("CSV batch preview, analysis, filtering, and export available: yes")
    print("Temporary human review and reviewed export available: yes")
    return 0
