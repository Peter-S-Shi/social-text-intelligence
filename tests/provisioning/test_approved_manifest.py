"""The approved models are fixed; values come from docs/MODEL_PROVISIONING.md."""

from __future__ import annotations

from pathlib import Path

from social_text_intelligence.application.model_provisioning import APPROVED_MODELS
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.model_store import (
    LocalModelProvisioner,
    local_model_provisioner,
)
from social_text_intelligence.providers import (
    EMOTION_MODEL_ID,
    EMOTION_MODEL_REVISION,
    MODEL_ID,
    MODEL_REVISION,
)


def test_the_manifest_pins_the_two_approved_models_and_licences() -> None:
    assert [
        (spec.key, spec.model_id, spec.revision, spec.license, spec.total_bytes)
        for spec in APPROVED_MODELS
    ] == [
        (
            "sentiment",
            "cardiffnlp/twitter-roberta-base-sentiment-latest",
            "3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7",
            "CC-BY-4.0",
            502_401_839,
        ),
        (
            "emotion",
            "SamLowe/roberta-base-go_emotions",
            "d75048347613a25d77de8cf6412eaae9fa7b26be",
            "MIT",
            502_063_093,
        ),
    ]
    assert [f.name for f in APPROVED_MODELS[0].files] == [
        "config.json",
        "merges.txt",
        "pytorch_model.bin",
        "special_tokens_map.json",
        "vocab.json",
    ]
    assert [f.name for f in APPROVED_MODELS[1].files] == [
        "config.json",
        "merges.txt",
        "model.safetensors",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.json",
    ]


def test_the_manifest_matches_what_the_providers_load() -> None:
    sentiment, emotion = APPROVED_MODELS
    assert (sentiment.model_id, sentiment.revision) == (MODEL_ID, MODEL_REVISION)
    assert (emotion.model_id, emotion.revision) == (
        EMOTION_MODEL_ID,
        EMOTION_MODEL_REVISION,
    )


def test_the_production_provisioner_uses_the_per_user_models_folder(
    tmp_path: Path,
) -> None:
    locations = AppDataLocations(tmp_path / "SocialTextIntelligence")

    provisioner = local_model_provisioner(locations)

    assert locations.models_dir == tmp_path / "SocialTextIntelligence" / "models"
    assert isinstance(provisioner, LocalModelProvisioner)
    assert provisioner.models_root == locations.models_dir
    assert not provisioner.status().ready
    assert not locations.root.exists()
