"""Opt-in: fetch small pinned files from the original repositories over HTTPS."""

import hashlib
import os
import unittest

from social_text_intelligence.application.model_provisioning import APPROVED_MODELS
from social_text_intelligence.infrastructure.model_download import (
    UrllibDownloadTransport,
    pinned_file_url,
)


@unittest.skipUnless(
    os.environ.get("STI_RUN_NETWORK_TESTS") == "1",
    "set STI_RUN_NETWORK_TESTS=1 to contact the model repositories",
)
class PinnedDownloadNetworkTests(unittest.TestCase):
    def test_small_pinned_files_match_the_manifest_and_resume_by_range(self) -> None:
        transport = UrllibDownloadTransport()
        for spec in APPROVED_MODELS:
            item = next(f for f in spec.files if f.name == "config.json")
            url = pinned_file_url(spec.model_id, spec.revision, item.name)
            with transport.open(url, start=0) as stream:
                whole = b"".join(stream.chunks)
            self.assertEqual(hashlib.sha256(whole).hexdigest(), item.sha256)
            with transport.open(url, start=100) as stream:
                tail = b"".join(stream.chunks)
                resumed = stream.resumed
            self.assertEqual(tail if resumed else tail[100:], whole[100:])
