"""Packaged guide, synthetic ticket, and fixture provider tests."""

import unittest

from social_text_intelligence.contracts import (
    MockProvenance,
    TicketComplexity,
    TicketSource,
)
from social_text_intelligence.providers import FixtureTriageSuggestionProvider
from social_text_intelligence.services import (
    load_support_tickets,
    load_triage_guide,
)


class TriageResourceTests(unittest.TestCase):
    def test_versioned_guide_and_fixture_library_are_synthetic_and_stable(
        self,
    ) -> None:
        guide = load_triage_guide()
        tickets = load_support_tickets(guide)
        self.assertEqual(guide.guide_id, "sti-synthetic-support-triage-guide")
        self.assertEqual(guide.version, "1.0.0")
        self.assertIn("synthetic", guide.disclaimer.lower())
        self.assertEqual(len(guide.rule_ids), len(set(guide.rule_ids)))
        self.assertGreaterEqual(len(tickets), 20)
        self.assertLessEqual(len(tickets), 24)
        self.assertEqual(
            {ticket.complexity for ticket in tickets},
            set(TicketComplexity),
        )
        self.assertTrue(
            all(ticket.source is TicketSource.BUILT_IN_SYNTHETIC for ticket in tickets)
        )
        self.assertTrue(
            all(
                set(ticket.applicable_rule_ids) <= set(guide.rule_ids)
                for ticket in tickets
            )
        )
        self.assertTrue(any(ticket.mock_suggestion is None for ticket in tickets))
        self.assertTrue(any(ticket.mock_suggestion is not None for ticket in tickets))

    def test_fixture_provider_is_deterministic_and_provenance_is_explicit(
        self,
    ) -> None:
        tickets = load_support_tickets()
        provider = FixtureTriageSuggestionProvider()
        available = next(
            ticket for ticket in tickets if ticket.mock_suggestion is not None
        )
        unavailable = next(
            ticket for ticket in tickets if ticket.mock_suggestion is None
        )
        suggestion = provider.suggest(available)
        self.assertIsNotNone(suggestion)
        assert suggestion is not None
        self.assertIs(suggestion.provenance, MockProvenance.BUILT_IN_MOCK)
        self.assertIs(provider.suggest(available), suggestion)
        self.assertIsNone(provider.suggest(unavailable))


if __name__ == "__main__":
    unittest.main()
