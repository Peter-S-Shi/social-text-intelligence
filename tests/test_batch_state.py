"""Tests for bounded, expiring in-memory batch state."""

import unittest

from social_text_intelligence.interface.batch_state import (
    BatchWorkspace,
    EphemeralBatchStore,
)


class BatchStateTests(unittest.TestCase):
    def test_workspace_expires_without_disk_persistence(self) -> None:
        now = 100.0
        store = EphemeralBatchStore(ttl_seconds=10, clock=lambda: now)
        token = store.create(BatchWorkspace())
        self.assertIsNotNone(store.get(token))

        now = 111.0
        self.assertIsNone(store.get(token))

    def test_capacity_evicts_oldest_workspace(self) -> None:
        now = 10.0
        store = EphemeralBatchStore(capacity=1, clock=lambda: now)
        first = store.create(BatchWorkspace())
        now = 11.0
        second = store.create(BatchWorkspace())
        self.assertIsNone(store.get(first))
        self.assertIsNotNone(store.get(second))
