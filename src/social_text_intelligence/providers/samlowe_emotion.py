"""Pinned local multi-label inference for Sam Lowe's GoEmotions model."""

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
    ValidationError,
)
from ..contracts.inputs import NormalizedTextInput
from ..contracts.results import (
    EmotionLabel,
    EmotionResult,
    EmotionScore,
    NativeScore,
    ProviderMetadata,
    TaskType,
)
from .input_budget import encode_complete_text, resolve_model_input_budget

EMOTION_MODEL_ID = "SamLowe/roberta-base-go_emotions"
EMOTION_MODEL_REVISION = "d75048347613a25d77de8cf6412eaae9fa7b26be"
EMOTION_MODEL_INPUT_TOKEN_LIMIT = 512
DEFAULT_EMOTION_THRESHOLD = 0.5
NATIVE_EMOTION_LABELS = (
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
)

COMPACT_EMOTION_MAPPING = {
    EmotionLabel.JOY: ("joy", "excitement", "love", "optimism", "relief"),
    EmotionLabel.AMUSEMENT: ("amusement",),
    EmotionLabel.ADMIRATION: ("admiration", "approval", "pride"),
    EmotionLabel.GRATITUDE: ("gratitude",),
    EmotionLabel.ANGER: ("anger", "annoyance"),
    EmotionLabel.SADNESS: (
        "sadness",
        "disappointment",
        "grief",
        "remorse",
    ),
    EmotionLabel.FEAR: ("fear", "nervousness"),
    EmotionLabel.DISGUST: ("disgust",),
    EmotionLabel.NEUTRAL: ("neutral",),
}
UNMAPPED_NATIVE_LABELS = (
    "caring",
    "confusion",
    "curiosity",
    "desire",
    "disapproval",
    "embarrassment",
    "realization",
    "surprise",
)


class EmotionRuntime(Protocol):
    """Minimal runtime boundary used to keep fast tests model-free."""

    def predict(self, text: str) -> Sequence[float]:
        """Return independent probabilities in native-label order."""
        ...

    def validate_input(self, text: str) -> None:
        """Reject text the pinned model cannot consume in full."""
        ...


class TransformersEmotionRuntime:
    """Load immutable Safetensors weights and execute local multi-label inference."""

    def __init__(self, *, cache_dir: Path, offline: bool) -> None:
        try:
            torch = importlib.import_module("torch")
            transformers = importlib.import_module("transformers")
        except ImportError as error:
            raise ProviderError(
                provider="samlowe-transformers",
                code="missing_model_dependencies",
                message='Local emotion dependencies are missing. Install ".[emotion]".',
            ) from error

        load_options = {
            "cache_dir": str(cache_dir),
            "local_files_only": offline,
            "revision": EMOTION_MODEL_REVISION,
            "trust_remote_code": False,
        }
        try:
            self._tokenizer = transformers.AutoTokenizer.from_pretrained(
                EMOTION_MODEL_ID,
                **load_options,
            )
            model_class = transformers.AutoModelForSequenceClassification
            self._model = model_class.from_pretrained(
                EMOTION_MODEL_ID,
                use_safetensors=True,
                weights_only=True,
                **load_options,
            )
        except (OSError, ValueError) as error:
            mode = "the local cache" if offline else "the pinned model source"
            raise ProviderError(
                provider="samlowe-transformers",
                code="model_load_failed",
                message=f"Could not load the licensed emotion model from {mode}.",
            ) from error

        self._torch: Any = torch
        self._model.eval()
        self._max_input_tokens = resolve_model_input_budget(
            tokenizer=self._tokenizer,
            model=self._model,
            provider="samlowe-transformers",
            approved_max_input_tokens=EMOTION_MODEL_INPUT_TOKEN_LIMIT,
        )

    def _encode_complete(self, text: str) -> Any:
        return encode_complete_text(
            tokenizer=self._tokenizer,
            text=text,
            provider="samlowe-transformers",
            max_input_tokens=self._max_input_tokens,
        )

    def validate_input(self, text: str) -> None:
        self._encode_complete(text)

    def predict(self, text: str) -> Sequence[float]:
        encoded = self._encode_complete(text)
        with self._torch.inference_mode():
            logits = self._model(**encoded).logits[0]
            probabilities = self._torch.sigmoid(logits).tolist()
        return tuple(float(score) for score in probabilities)


@dataclass(slots=True)
class SamLoweEmotionProvider:
    """Map native GoEmotions probabilities into the compact project taxonomy."""

    threshold: float = DEFAULT_EMOTION_THRESHOLD
    cache_dir: Path = Path("model_cache")
    offline: bool = False
    runtime: EmotionRuntime | None = None
    metadata: ProviderMetadata = field(
        default_factory=lambda: ProviderMetadata(
            provider="samlowe-transformers",
            model_name=EMOTION_MODEL_ID,
            revision=EMOTION_MODEL_REVISION,
            task=TaskType.EMOTION,
            supported_languages=("en",),
            native_labels=NATIVE_EMOTION_LABELS,
        ),
        init=False,
    )

    def __post_init__(self) -> None:
        if not math.isfinite(self.threshold) or not 0.0 < self.threshold <= 1.0:
            raise ValidationError(
                field="emotion_threshold",
                code="invalid_threshold",
                message="emotion_threshold must be greater than 0 and at most 1.",
            )

    def analyze(self, record: NormalizedTextInput) -> EmotionResult:
        self._validate_language(record)
        runtime = self._runtime()

        probabilities = tuple(float(score) for score in runtime.predict(record.text))
        self._validate_probabilities(probabilities)
        native_scores = tuple(
            NativeScore(label=label, score=score)
            for label, score in zip(NATIVE_EMOTION_LABELS, probabilities, strict=True)
        )
        native_by_label = {item.label: item.score for item in native_scores}
        scores = tuple(
            EmotionScore(
                label=label,
                score=max(
                    native_by_label[item] for item in COMPACT_EMOTION_MAPPING[label]
                ),
            )
            for label in EmotionLabel
        )
        score_by_label = {item.label: item.score for item in scores}
        activated = tuple(
            sorted(
                (
                    label
                    for label in EmotionLabel
                    if label is not EmotionLabel.NEUTRAL
                    and score_by_label[label] >= self.threshold
                ),
                key=lambda label: (-score_by_label[label], label.value),
            )
        )
        dominant = activated[0] if activated else EmotionLabel.NEUTRAL
        secondary = activated[1:] if activated else ()
        return EmotionResult(
            record_id=record.record_id,
            dominant_emotion=dominant,
            confidence=score_by_label[dominant],
            threshold=self.threshold,
            secondary_emotions=secondary,
            scores=scores,
            native_scores=native_scores,
            provider=self.metadata,
        )

    def validate_input(self, record: NormalizedTextInput) -> None:
        self._validate_language(record)
        self._runtime().validate_input(record.text)

    def _runtime(self) -> EmotionRuntime:
        runtime = self.runtime
        if runtime is None:
            runtime = TransformersEmotionRuntime(
                cache_dir=self.cache_dir,
                offline=self.offline,
            )
            self.runtime = runtime
        return runtime

    def _validate_language(self, record: NormalizedTextInput) -> None:
        if record.language is not None:
            primary_language = record.language.split("-", maxsplit=1)[0].lower()
            if primary_language != "en":
                raise UnsupportedLanguageError(
                    provider=self.metadata.provider,
                    language=record.language,
                )

    def _validate_probabilities(self, probabilities: tuple[float, ...]) -> None:
        if len(probabilities) != len(NATIVE_EMOTION_LABELS) or not all(
            math.isfinite(score) and 0.0 <= score <= 1.0
            for score in probabilities
        ):
            raise InvalidProviderOutputError(
                provider=self.metadata.provider,
                message=(
                    "The emotion runtime must return 28 independent finite "
                    "probabilities between zero and one."
                ),
            )
