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
from .services.analysis import SentimentAnalysisService


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
        print("Emotion providers: interfaces and deterministic mocks only")
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

    print(PROJECT_STATUS.name)
    print(f"Milestone: {PROJECT_STATUS.milestone}")
    print("Local-first: yes")
    print("Analysis contracts available: yes")
    print("Local sentiment inference available: yes")
    print("Emotion model inference available: no")
    return 0
