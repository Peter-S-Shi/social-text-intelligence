"""Applied filter/sort/selection state reflection regressions (FCR-052)."""

import io
import unittest

from social_text_intelligence.contracts import EmotionLabel, SentimentLabel
from social_text_intelligence.interface import create_app
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import AnalysisService, LazyAnalysisService


def gateway() -> LazyAnalysisService:
    return LazyAnalysisService(
        lambda: AnalysisService(
            sentiment_provider=DeterministicSentimentProvider(
                SentimentLabel.POSITIVE
            ),
            emotion_provider=DeterministicEmotionProvider(EmotionLabel.GRATITUDE),
        )
    )


def valid_form() -> dict[str, object]:
    return {
        "primary_intent": "recover_account_access",
        "secondary_intents": [],
        "issue_category": "account_and_access",
        "urgency": "high",
        "recommended_queue": "account_and_access",
        "escalation_required": "false",
        "escalation_reason": "",
        "primary_next_action": "verify_identity_or_account_ownership",
        "secondary_next_actions": [],
        "unclear_reason": "",
        "human_notes": "",
    }


class TriageAppliedStateReflectionTests(unittest.TestCase):
    """support-001 stays untriaged; support-002 is finalized urgency=high,
    escalation_required=false, queue=account_and_access. Their text never
    overlaps on the word "password", which only appears in support-001."""

    def setUp(self) -> None:
        self.app = create_app(
            {"TESTING": True, "MAX_BATCH_BYTES": 10_000, "MAX_BATCH_ROWS": 10},
            analysis_gateway=gateway(),
        )
        self.client = self.app.test_client()
        started = self.client.post(
            "/triage/start", data={"mode": "independent", "batch_token": ""}
        )
        self.base = started.headers["Location"].removesuffix("/guide")
        self.client.post(
            self.base + "/synthetic",
            data={"ticket_ids": ["support-001", "support-002"]},
        )
        finalized = self.client.post(
            self.base + "/tickets/support-002/finalize", data=valid_form()
        )
        self.assertEqual(finalized.status_code, 302)

    def test_default_view_shows_only_default_selected_options(self) -> None:
        page = self.client.get(self.base + "/workspace")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'<option value="" selected>All</option>', page.data)
        self.assertIn(
            b'<option value="original" selected>Original order</option>',
            page.data,
        )
        self.assertIn(b'<input name="q" value="">', page.data)
        self.assertNotIn(b' selected>high</option>', page.data)
        self.assertNotIn(b' selected>finalized</option>', page.data)

    def test_status_filter_applies_and_select_reflects_it(self) -> None:
        page = self.client.get(self.base + "/workspace?status=finalized")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b">support-002<", page.data)
        self.assertNotIn(b">support-001<", page.data)
        self.assertIn(
            b'<option value="finalized" selected>finalized</option>', page.data
        )
        self.assertIn(b'<option value="" selected>All</option>', page.data)

    def test_urgency_filter_applies_and_select_reflects_it(self) -> None:
        page = self.client.get(self.base + "/workspace?urgency=high")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b">support-002<", page.data)
        self.assertNotIn(b">support-001<", page.data)
        self.assertIn(b'<option value="high" selected>high</option>', page.data)

    def test_tri_state_boolean_filter_true_and_false_both_reflect(self) -> None:
        false_page = self.client.get(self.base + "/workspace?escalation=false")
        self.assertEqual(false_page.status_code, 200)
        self.assertIn(b">support-002<", false_page.data)
        self.assertIn(
            b'<option value="false" selected>No</option>', false_page.data
        )

        true_page = self.client.get(self.base + "/workspace?escalation=true")
        self.assertEqual(true_page.status_code, 200)
        self.assertNotIn(b">support-002<", true_page.data)
        self.assertNotIn(b">support-001<", true_page.data)
        self.assertIn(
            b'<option value="true" selected>Yes</option>', true_page.data
        )

    def test_text_search_applies_and_input_reflects_value(self) -> None:
        page = self.client.get(self.base + "/workspace?q=password")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b">support-001<", page.data)
        self.assertNotIn(b">support-002<", page.data)
        self.assertIn(b'<input name="q" value="password">', page.data)

    def test_sort_select_reflects_the_applied_sort(self) -> None:
        page = self.client.get(self.base + "/workspace?sort=urgency")
        self.assertEqual(page.status_code, 200)
        self.assertIn(
            b'<option value="urgency" selected>Urgency</option>', page.data
        )
        self.assertNotIn(
            b'<option value="original" selected>Original order</option>',
            page.data,
        )

    def test_previously_correct_text_inputs_are_unaffected(self) -> None:
        page = self.client.get(
            self.base + "/workspace?topic=billing&community=beta"
        )
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'<input name="topic" value="billing">', page.data)
        self.assertIn(b'<input name="community" value="beta">', page.data)


class ModerationAppliedStateReflectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(
            {"TESTING": True, "MAX_BATCH_BYTES": 10_000, "MAX_BATCH_ROWS": 10},
            analysis_gateway=gateway(),
        )
        self.client = self.app.test_client()
        started = self.client.post(
            "/moderation/start", data={"batch_token": ""}
        )
        self.base = started.headers["Location"].removesuffix("/prepare")

    def test_default_view_shows_only_default_selected_options(self) -> None:
        page = self.client.get(self.base + "/prepare")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'<option value="" selected>all</option>', page.data)
        self.assertNotIn(b' selected>beginner</option>', page.data)

    def test_difficulty_filter_applies_and_select_reflects_it(self) -> None:
        page = self.client.get(self.base + "/prepare?difficulty=beginner")
        self.assertEqual(page.status_code, 200)
        self.assertIn(
            b'<option value="beginner" selected>beginner</option>', page.data
        )
        self.assertNotIn(b"intermediate</div>", page.data)
        self.assertNotIn(b"advanced</div>", page.data)

    def test_safety_sensitive_tri_state_filter_reflects_true_and_false(
        self,
    ) -> None:
        false_page = self.client.get(
            self.base + "/prepare?safety_sensitive=false"
        )
        self.assertEqual(false_page.status_code, 200)
        self.assertIn(
            b'<option value="false" selected>no</option>', false_page.data
        )

        true_page = self.client.get(
            self.base + "/prepare?safety_sensitive=true"
        )
        self.assertEqual(true_page.status_code, 200)
        self.assertIn(
            b'<option value="true" selected>yes</option>', true_page.data
        )

    def test_combined_non_default_filters_narrow_results_and_all_reflect(
        self,
    ) -> None:
        page = self.client.get(
            self.base + "/prepare?difficulty=beginner&safety_sensitive=false"
        )
        self.assertEqual(page.status_code, 200)
        self.assertIn(
            b'<option value="beginner" selected>beginner</option>', page.data
        )
        self.assertIn(
            b'<option value="false" selected>no</option>', page.data
        )
        self.assertIn(b"synthetic-001", page.data)


class InsightsExampleSelectionReflectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(
            {
                "TESTING": True,
                "MAX_BATCH_BYTES": 20_000,
                "MAX_BATCH_ROWS": 20,
                "MAX_TEXT_LENGTH": 100,
            },
            analysis_gateway=gateway(),
        )
        self.client = self.app.test_client()
        rows = ["record_id,text"] + [
            f"row-{n},Synthetic representative row {n}." for n in range(1, 4)
        ]
        uploaded = self.client.post(
            "/batch/upload",
            data={
                "file": (
                    io.BytesIO(("\n".join(rows) + "\n").encode()),
                    "synthetic.csv",
                )
            },
            content_type="multipart/form-data",
        )
        workspace_url = uploaded.headers["Location"]
        self.client.post(workspace_url + "/analyze")
        self.insight_url = workspace_url + "/insights"

    def _checkbox(self, record_id: str) -> bytes:
        return f'value="{record_id}" checked'.encode()

    def test_user_selected_mode_applies_selection_and_checks_matching_boxes(
        self,
    ) -> None:
        page = self.client.get(
            self.insight_url
            + "?view=examples&example_mode=user_selected"
            + "&record_id=row-1&record_id=row-2"
        )
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"row-1", page.data)
        self.assertIn(b"row-2", page.data)
        self.assertNotIn(b"Synthetic representative row 3.", page.data)
        self.assertIn(self._checkbox("row-1"), page.data)
        self.assertIn(self._checkbox("row-2"), page.data)
        self.assertNotIn(self._checkbox("row-3"), page.data)

    def test_non_selecting_mode_does_not_falsely_check_leftover_record_ids(
        self,
    ) -> None:
        """record_id has no effect outside user_selected mode, so it must not
        be shown as an effective (checked) selection either."""

        page = self.client.get(
            self.insight_url
            + "?view=examples&example_mode=lowest_ai_confidence&record_id=row-1"
        )
        self.assertEqual(page.status_code, 200)
        self.assertNotIn(self._checkbox("row-1"), page.data)

    def test_default_examples_view_has_no_checked_record_boxes(self) -> None:
        page = self.client.get(self.insight_url + "?view=examples")
        self.assertEqual(page.status_code, 200)
        self.assertNotIn(b"checked", page.data)


if __name__ == "__main__":
    unittest.main()
