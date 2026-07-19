"""Privacy-conscious local Flask interface for direct text analysis."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from flask import Flask, render_template, request

from ..contracts import AnalysisReport, NormalizedTextInput
from ..contracts.errors import (
    ProviderError,
    SocialTextIntelligenceError,
    ValidationError,
)
from ..providers import CardiffSentimentProvider, SamLoweEmotionProvider
from ..providers.samlowe_emotion import DEFAULT_EMOTION_THRESHOLD
from ..services import AnalysisService, LazyAnalysisService


class AnalysisGateway(Protocol):
    @property
    def initialized(self) -> bool: ...

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport: ...


def _real_analysis_service(
    *, cache_dir: Path, offline: bool, emotion_threshold: float
) -> AnalysisService:
    return AnalysisService(
        sentiment_provider=CardiffSentimentProvider(
            cache_dir=cache_dir,
            offline=offline,
        ),
        emotion_provider=SamLoweEmotionProvider(
            cache_dir=cache_dir,
            offline=offline,
            threshold=emotion_threshold,
        ),
    )


def _safe_error(error: Exception) -> str:
    if isinstance(error, ValidationError):
        return error.message
    if isinstance(error, ProviderError):
        if error.code == "missing_model_dependencies":
            return (
                "Local model dependencies are not installed. "
                "Install the model extras."
            )
        if error.code == "model_load_failed":
            return (
                "The approved model files could not be loaded. In offline mode, "
                "confirm that both pinned revisions are already cached."
            )
        return error.message
    if isinstance(error, SocialTextIntelligenceError):
        return str(error)
    return "Analysis failed safely. Review the local setup and try again."


def create_app(
    config: Mapping[str, Any] | None = None,
    *,
    analysis_gateway: AnalysisGateway | None = None,
) -> Flask:
    """Create the local app without loading either model."""

    app = Flask(__name__)
    app.config.from_mapping(
        CACHE_DIR="model_cache",
        OFFLINE=False,
        EMOTION_THRESHOLD=DEFAULT_EMOTION_THRESHOLD,
        MAX_TEXT_LENGTH=20_000,
    )
    if config is not None:
        app.config.update(config)

    if analysis_gateway is None:
        cache_dir = Path(str(app.config["CACHE_DIR"]))
        offline = bool(app.config["OFFLINE"])
        threshold = float(app.config["EMOTION_THRESHOLD"])
        analysis_gateway = LazyAnalysisService(
            lambda: _real_analysis_service(
                cache_dir=cache_dir,
                offline=offline,
                emotion_threshold=threshold,
            )
        )
    app.extensions["sti_analysis_gateway"] = analysis_gateway

    @app.route("/", methods=["GET", "POST"])
    def analyze_text() -> str:
        report: AnalysisReport | None = None
        error_message: str | None = None
        text = ""
        if request.method == "POST":
            text = request.form.get("text", "")
            try:
                record = NormalizedTextInput.from_text(
                    text,
                    language="en",
                    max_text_length=int(app.config["MAX_TEXT_LENGTH"]),
                )
                report = analysis_gateway.analyze(record)
            # The interface boundary must never expose traceback text.
            except Exception as error:
                error_message = _safe_error(error)

        return render_template(
            "analyze.html",
            report=report,
            error_message=error_message,
            submitted_text=text,
            offline=bool(app.config["OFFLINE"]),
            initialized=analysis_gateway.initialized,
            max_text_length=int(app.config["MAX_TEXT_LENGTH"]),
        )

    return app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local STI Flask interface.")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--cache-dir", default="model_cache")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument(
        "--emotion-threshold", type=float, default=DEFAULT_EMOTION_THRESHOLD
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    app = create_app(
        {
            "CACHE_DIR": args.cache_dir,
            "OFFLINE": args.offline,
            "EMOTION_THRESHOLD": args.emotion_threshold,
        }
    )
    app.run(host="127.0.0.1", port=args.port, debug=False)
    return 0
