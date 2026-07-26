"""Bounded, sliding-expiry support triage state tests."""

import unittest

from social_text_intelligence.contracts import TriageMode
from social_text_intelligence.interface.triage_state import EphemeralTriageStore
from social_text_intelligence.services import new_triage_workspace


class TriageStateTests(unittest.TestCase):
    def test_capacity_blocks_without_eviction_and_clear_releases_capacity(
        self,
    ) -> None:
        store = EphemeralTriageStore(capacity=1)
        token = store.create(new_triage_workspace(mode=TriageMode.INDEPENDENT))
        with self.assertRaisesRegex(RuntimeError, "capacity"):
            store.create(new_triage_workspace(mode=TriageMode.INDEPENDENT))
        self.assertIsNotNone(store.get(token))
        store.delete(token)
        self.assertIsNotNone(
            store.create(new_triage_workspace(mode=TriageMode.INDEPENDENT))
        )

    def test_sliding_expiry_and_random_tokens(self) -> None:
        time = [0.0]
        store = EphemeralTriageStore(
            ttl_seconds=10, clock=lambda: time[0], capacity=2
        )
        first = store.create(new_triage_workspace(mode=TriageMode.INDEPENDENT))
        second = store.create(new_triage_workspace(mode=TriageMode.MOCK_ASSISTED))
        self.assertNotEqual(first, second)
        time[0] = 9.0
        self.assertIsNotNone(store.get(first))
        time[0] = 11.0
        self.assertIsNone(store.get(second))
        time[0] = 18.0
        self.assertIsNotNone(store.get(first))
        time[0] = 29.0
        self.assertIsNone(store.get(first))


if __name__ == "__main__":
    unittest.main()
