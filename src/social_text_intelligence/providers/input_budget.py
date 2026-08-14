"""Shared complete-input validation for pinned transformer providers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..contracts.errors import ModelInputTooLongError, ProviderError

_MAX_REASONABLE_TOKENIZER_LIMIT = 1_000_000


def resolve_model_input_budget(
    *,
    tokenizer: Any,
    model: Any,
    provider: str,
    approved_max_input_tokens: int,
) -> int:
    """Verify an audited pinned-model budget against loaded runtime metadata."""

    tokenizer_limit = getattr(tokenizer, "model_max_length", None)
    model_config = getattr(model, "config", None)
    model_limit = getattr(model_config, "max_position_embeddings", None)
    tokenizer_has_finite_limit = (
        isinstance(tokenizer_limit, int)
        and not isinstance(tokenizer_limit, bool)
        and 0 < tokenizer_limit <= _MAX_REASONABLE_TOKENIZER_LIMIT
    )
    if (
        not isinstance(approved_max_input_tokens, int)
        or isinstance(approved_max_input_tokens, bool)
        or approved_max_input_tokens <= 0
        or (
            tokenizer_has_finite_limit
            and tokenizer_limit != approved_max_input_tokens
        )
        or not isinstance(model_limit, int)
        or isinstance(model_limit, bool)
        or model_limit < approved_max_input_tokens
    ):
        raise ProviderError(
            provider=provider,
            code="invalid_model_input_budget",
            message=(
                "The pinned tokenizer and model do not expose a compatible finite "
                "encoded-input limit. Analysis was not performed."
            ),
        )
    return approved_max_input_tokens


def encode_complete_text(
    *,
    tokenizer: Any,
    text: str,
    provider: str,
    max_input_tokens: int,
) -> Mapping[str, Any]:
    """Encode without truncation and reject if the real sequence exceeds budget."""

    encoded: Mapping[str, Any] = tokenizer(
        text,
        add_special_tokens=True,
        truncation=False,
        return_tensors="pt",
    )
    input_ids = encoded.get("input_ids")
    shape = getattr(input_ids, "shape", None)
    if shape is None or len(shape) < 2:
        raise ProviderError(
            provider=provider,
            code="invalid_tokenizer_output",
            message="The pinned tokenizer returned an invalid encoded sequence.",
        )
    encoded_length = int(shape[-1])
    if encoded_length > max_input_tokens:
        raise ModelInputTooLongError(
            provider=provider,
            encoded_length=encoded_length,
            max_input_tokens=max_input_tokens,
        )
    return encoded
