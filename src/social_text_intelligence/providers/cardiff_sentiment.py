"""Pinned local inference for Cardiff NLP's English sentiment model."""

from __future__ import annotations

import importlib
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ..contracts.errors import (
    InvalidProviderOutputError,
    ProviderError,
    UnsupportedLanguageError,
)
from ..contracts.inputs import NormalizedTextInput
from ..contracts.results import (
    NativeScore,
    ProviderMetadata,
    SentimentLabel,
    SentimentResult,
    SentimentScore,
    TaskType,
)

MODEL_ID = "cardiffnlp/twitter-roberta-base-sentiment-latest"
MODEL_REVISION = "3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7"
NATIVE_LABELS = ("negative", "neutral", "positive")
_LABEL_MAP = {
    "negative": SentimentLabel.NEGATIVE,
    "neutral": SentimentLabel.NEUTRAL,
    "positive": SentimentLabel.POSITIVE,
}


class SentimentRuntime(Protocol):
    """Minimal runtime boundary used to keep unit tests model-free."""

    def predict(self, text: str) -> Sequence[float]:
        """Return probabilities in the provider's documented native-label order."""
        ...


def preprocess_social_text(text: str) -> str:
    """Apply the username and URL placeholders documented by the model author."""

    tokens: list[str] = []
    for token in text.split():
        if len(token) > 1 and token.startswith("@") and token.count("@") == 1:
            token = "@user"
        elif token.startswith("http"):
            token = "http"
        tokens.append(token)
    return " ".join(tokens)


class TransformersSentimentRuntime:
    """Load the immutable model revision and execute inference on the local machine."""

    def __init__(self, *, cache_dir: Path, offline: bool) -> None:
        try:
            torch = importlib.import_module("torch")
            transformers = importlib.import_module("transformers")
        except ImportError as error:
            raise ProviderError(
                provider="cardiffnlp-transformers",
                code="missing_model_dependencies",
                message=(
                    'Local sentiment dependencies are missing. Install ".[sentiment]".'
                ),
            ) from error

        load_options = {
            "cache_dir": str(cache_dir),
            "local_files_only": offline,
            "revision": MODEL_REVISION,
            "trust_remote_code": False,
        }
        try:
            self._tokenizer = transformers.AutoTokenizer.from_pretrained(
                MODEL_ID,
                **load_options,
            )
            model_class = transformers.AutoModelForSequenceClassification
            self._model = model_class.from_pretrained(
                MODEL_ID, weights_only=True, **load_options
            )
        except (OSError, ValueError) as error:
            mode = "the local cache" if offline else "the pinned model source"
            raise ProviderError(
                provider="cardiffnlp-transformers",
                code="model_load_failed",
                message=f"Could not load the licensed sentiment model from {mode}.",
            ) from error

        self._torch: Any = torch
        self._model.eval()

    def predict(self, text: str) -> Sequence[float]:
        encoded = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )
        with self._torch.inference_mode():
            logits = self._model(**encoded).logits[0]
            probabilities = self._torch.softmax(logits, dim=-1).tolist()
        return tuple(float(score) for score in probabilities)


@dataclass(slots=True)
class CardiffSentimentProvider:
    """Normalize one English sentiment prediction into application contracts."""

    cache_dir: Path = Path("model_cache")
    offline: bool = False
    runtime: SentimentRuntime | None = None
    metadata: ProviderMetadata = field(
        default_factory=lambda: ProviderMetadata(
            provider="cardiffnlp-transformers",
            model_name=MODEL_ID,
            revision=MODEL_REVISION,
            task=TaskType.SENTIMENT,
            supported_languages=("en",),
            native_labels=NATIVE_LABELS,
        ),
        init=False,
    )

    def analyze(self, record: NormalizedTextInput) -> SentimentResult:
        if record.language is not None:
            primary_language = record.language.split("-", maxsplit=1)[0].lower()
            if primary_language != "en":
                raise UnsupportedLanguageError(
                    provider=self.metadata.provider,
                    language=record.language,
                )

        runtime = self.runtime
        if runtime is None:
            runtime = TransformersSentimentRuntime(
                cache_dir=self.cache_dir,
                offline=self.offline,
            )
            self.runtime = runtime

        prepared_text = preprocess_social_text(record.text)
        probabilities = tuple(float(score) for score in runtime.predict(prepared_text))
        self._validate_probabilities(probabilities)

        native_scores = tuple(
            NativeScore(label=label, score=score)
            for label, score in zip(NATIVE_LABELS, probabilities, strict=True)
        )
        scores = tuple(
            SentimentScore(label=_LABEL_MAP[item.label], score=item.score)
            for item in native_scores
        )
        selected = max(scores, key=lambda item: item.score)
        return SentimentResult(
            record_id=record.record_id,
            label=selected.label,
            confidence=selected.score,
            scores=scores,
            native_scores=native_scores,
            provider=self.metadata,
        )

    def _validate_probabilities(self, probabilities: tuple[float, ...]) -> None:
        valid_values = all(
            math.isfinite(score) and 0.0 <= score <= 1.0
            for score in probabilities
        )
        if (
            len(probabilities) != len(NATIVE_LABELS)
            or not valid_values
            or not math.isclose(sum(probabilities), 1.0, abs_tol=1e-4)
        ):
            raise InvalidProviderOutputError(
                provider=self.metadata.provider,
                message=(
                    "The sentiment runtime must return three finite probabilities "
                    "that sum to one."
                ),
            )
