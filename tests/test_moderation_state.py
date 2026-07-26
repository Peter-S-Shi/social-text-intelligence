"""Bounded and expiring process-memory moderation workspace tests."""

import unittest

from social_text_intelligence.interface.moderation_state import (
    EphemeralModerationStore,
)
from social_text_intelligence.services import ModerationWorkspace


class ModerationStateTests(unittest.TestCase):
    def test_workspace_expires_and_is_not_persisted(self) -> None:
        now = 100.0
        store = EphemeralModerationStore(
            ttl_seconds=10, clock=lambda: now
        )
        token = store.create(ModerationWorkspace())
        self.assertIsNotNone(store.get(token))

        now = 111.0
        self.assertIsNone(store.get(token))

    def test_capacity_blocks_without_silent_eviction(self) -> None:
        store = EphemeralModerationStore(capacity=1)
        first = store.create(ModerationWorkspace())
        with self.assertRaisesRegex(RuntimeError, "capacity reached"):
            store.create(ModerationWorkspace())
        self.assertIsNotNone(store.get(first))


if __name__ == "__main__":
    unittest.main()
