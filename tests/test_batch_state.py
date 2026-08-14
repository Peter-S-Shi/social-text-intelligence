"""Tests for bounded, expiring in-memory batch state."""

import unittest

from social_text_intelligence.interface.batch_state import (
    BatchWorkspace,
    EphemeralBatchStore,
)
from social_text_intelligence.interface.workspace_mutation import (
    WorkspaceMutationConflict,
)


class BatchStateTests(unittest.TestCase):
    def test_workspace_expires_without_disk_persistence(self) -> None:
        now = 100.0
        store = EphemeralBatchStore(ttl_seconds=10, clock=lambda: now)
        token = store.create(BatchWorkspace())
        self.assertIsNotNone(store.get(token))

        now = 111.0
        self.assertIsNone(store.get(token))

    def test_capacity_blocks_without_eviction_and_clear_releases_capacity(
        self,
    ) -> None:
        now = 10.0
        store = EphemeralBatchStore(capacity=1, clock=lambda: now)
        first = store.create(BatchWorkspace())
        now = 11.0
        with self.assertRaisesRegex(RuntimeError, "capacity reached"):
            store.create(BatchWorkspace())
        self.assertIsNotNone(store.get(first))
        store.delete(first)
        self.assertIsNotNone(store.create(BatchWorkspace()))

    def test_active_analysis_survives_expiry_and_commits_atomically(self) -> None:
        now = 100.0
        original = BatchWorkspace()
        completed = BatchWorkspace()
        store = EphemeralBatchStore(
            ttl_seconds=10, capacity=1, clock=lambda: now
        )
        token = store.create(original)
        lease = store.begin_analysis(token)
        self.assertIsNotNone(lease)
        assert lease is not None

        now = 111.0
        with self.assertRaisesRegex(RuntimeError, "capacity reached"):
            store.create(BatchWorkspace())
        with self.assertRaisesRegex(RuntimeError, "cannot be cleared"):
            store.delete(token)
        with self.assertRaisesRegex(
            WorkspaceMutationConflict, "being analyzed"
        ):
            store.mutate(token, lambda current: current)
        self.assertTrue(store.complete_analysis(lease, completed))
        self.assertIs(store.get(token), completed)

    def test_stale_or_cancelled_analysis_cannot_write_back(self) -> None:
        store = EphemeralBatchStore()
        token = store.create(BatchWorkspace())
        lease = store.begin_analysis(token)
        self.assertIsNotNone(lease)
        assert lease is not None
        self.assertTrue(store.cancel_analysis(lease))
        self.assertFalse(store.complete_analysis(lease, BatchWorkspace()))
        self.assertIsNotNone(store.get(token))

    def test_expired_workspace_rejects_mutation_without_recreation(self) -> None:
        now = 100.0
        store = EphemeralBatchStore(ttl_seconds=10, clock=lambda: now)
        token = store.create(BatchWorkspace())
        now = 111.0
        self.assertIsNone(store.mutate(token, lambda current: current))
        self.assertIsNone(store.get(token))
