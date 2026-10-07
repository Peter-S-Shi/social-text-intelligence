"""Opt-in: provision the real pinned models from an existing cache, then analyse."""

import importlib.util
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from social_text_intelligence.application.model_provisioning import (
    build_provisioned_analysis_service,
)
from social_text_intelligence.application.settings import AppSettings
from social_text_intelligence.contracts import NormalizedTextInput, SentimentLabel
from social_text_intelligence.infrastructure.app_data import AppDataLocations
from social_text_intelligence.infrastructure.model_store import (
    local_model_provisioner,
)

_MODEL_TESTS_ENABLED = os.environ.get("STI_RUN_MODEL_TESTS") == "1"
_RUNTIME_AVAILABLE = all(
    importlib.util.find_spec(package) is not None
    for package in ("torch", "transformers")
)


@unittest.skipUnless(
    _MODEL_TESTS_ENABLED and _RUNTIME_AVAILABLE,
    "set STI_RUN_MODEL_TESTS=1, install the model extras, and point "
    "STI_MODEL_CACHE at a cache holding both pinned revisions",
)
class ModelProvisioningIntegrationTests(unittest.TestCase):
    def test_imported_models_are_verified_and_analyse_offline(self) -> None:
        source = Path(os.environ.get("STI_MODEL_CACHE", "model_cache"))
        with TemporaryDirectory() as app_data:
            provisioner = local_model_provisioner(AppDataLocations(Path(app_data)))
            self.assertEqual(
                provisioner.inspect_folder(source).importable_keys,
                ("sentiment", "emotion"),
            )

            result = provisioner.import_folder(source)

            self.assertTrue(result.status.ready, result)
            self.assertTrue(provisioner.verify().ready)
            gateway = build_provisioned_analysis_service(AppSettings(), provisioner)
            report = gateway.analyze(
                NormalizedTextInput.from_text(
                    "I am delighted that this synthetic test works so reliably!",
                    record_id="provisioning-integration-1",
                    language="en",
                )
            )
            self.assertEqual(report.sentiment.label, SentimentLabel.POSITIVE)
