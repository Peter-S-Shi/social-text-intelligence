"""Token-budget regressions for complete transformer input consumption."""

import unittest
from types import SimpleNamespace
from typing import Any

from social_text_intelligence.contracts import (
    ModelInputTooLongError,
    ProviderError,
)
from social_text_intelligence.providers.input_budget import (
    encode_complete_text,
    resolve_model_input_budget,
)


class FakeInputIds:
    def __init__(self, length: int) -> None:
        self.shape = (1, length)


class SpecialTokenTokenizer:
    model_max_length = 512

    def __init__(self) -> None:
        self.last_options: dict[str, Any] = {}

    def __call__(self, text: str, **options: Any) -> dict[str, FakeInputIds]:
        self.last_options = options
        # Each synthetic word is one content token, plus BOS and EOS.
        return {"input_ids": FakeInputIds(len(text.split()) + 2)}


class InputBudgetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tokenizer = SpecialTokenTokenizer()

    def test_exact_encoded_boundary_succeeds_without_truncation(self) -> None:
        encoded = encode_complete_text(
            tokenizer=self.tokenizer,
            text="token " * 510,
            provider="synthetic-provider",
            max_input_tokens=512,
        )

        self.assertEqual(encoded["input_ids"].shape, (1, 512))
        self.assertEqual(
            self.tokenizer.last_options,
            {
                "add_special_tokens": True,
                "truncation": False,
                "return_tensors": "pt",
            },
        )

    def test_one_encoded_token_over_boundary_is_explicitly_rejected(self) -> None:
        with self.assertRaises(ModelInputTooLongError) as raised:
            encode_complete_text(
                tokenizer=self.tokenizer,
                text="token " * 511,
                provider="synthetic-provider",
                max_input_tokens=512,
            )

        self.assertEqual(raised.exception.encoded_length, 513)
        self.assertEqual(raised.exception.max_input_tokens, 512)
        self.assertIn("including special tokens", raised.exception.message)

    def test_budget_comes_from_compatible_tokenizer_and_model_contract(self) -> None:
        model = SimpleNamespace(
            config=SimpleNamespace(max_position_embeddings=514)
        )
        self.assertEqual(
            resolve_model_input_budget(
                tokenizer=self.tokenizer,
                model=model,
                provider="synthetic-provider",
                approved_max_input_tokens=512,
            ),
            512,
        )

        # Cardiff's pinned tokenizer uses the Hugging Face unknown-limit sentinel;
        # the audited 512-token provider contract remains authoritative.
        self.tokenizer.model_max_length = 10**30
        self.assertEqual(
            resolve_model_input_budget(
                tokenizer=self.tokenizer,
                model=model,
                provider="synthetic-provider",
                approved_max_input_tokens=512,
            ),
            512,
        )

        self.tokenizer.model_max_length = 256
        with self.assertRaisesRegex(ProviderError, "compatible finite"):
            resolve_model_input_budget(
                tokenizer=self.tokenizer,
                model=model,
                provider="synthetic-provider",
                approved_max_input_tokens=512,
            )
