"""Support Triage timestamp ordering integrity regressions (FCR-051)."""

import unittest
from collections.abc import Callable
from pathlib import Path

from social_text_intelligence.contracts import (
    EmotionLabel,
    SentimentLabel,
    TicketComplexity,
    TriageMode,
)
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import (
    AnalysisService,
    TriageFilter,
    TriageLimits,
    TriageWorkspace,
    analyze_batch,
    filter_triage_entries,
    inspect_csv_upload,
    load_triage_guide,
    new_triage_workspace,
    prepare_csv_batch,
    prepare_workspace_ticket,
)

TEMPLATES = (
    Path(__file__).parents[1]
    / "src"
    / "social_text_intelligence"
    / "interface"
    / "templates"
)


def analyzer() -> AnalysisService:
    return AnalysisService(
        sentiment_provider=DeterministicSentimentProvider(SentimentLabel.POSITIVE),
        emotion_provider=DeterministicEmotionProvider(EmotionLabel.GRATITUDE),
    )


def fixed_ticket_id(value: str) -> Callable[[], str]:
    """Give each ticket a readable, assertion-friendly identity."""

    return lambda: value


class TriageTimestampOrderingTests(unittest.TestCase):
    """Cover the deterministic Sort: Timestamp contract end to end."""

    def setUp(self) -> None:
        self.guide = load_triage_guide()

    def workspace_with(
        self, timestamps: tuple[tuple[str, str], ...]
    ) -> TriageWorkspace:
        """Build a workspace whose tickets carry the supplied raw timestamps.

        Records travel the real CSV -> batch -> workspace-ticket path so the
        stored `source_timestamp` is produced exactly as production produces it.
        """

        rows = ["record_id,text,timestamp"]
        for record_id, timestamp in timestamps:
            rows.append(f"{record_id},Synthetic triage row {record_id}.,{timestamp}")
        pending = inspect_csv_upload(
            ("\n".join(rows) + "\n").encode(), max_bytes=100_000
        )
        preview = prepare_csv_batch(
            pending, text_column="text", max_rows=50, max_text_length=200
        )
        result = analyze_batch(preview, analyzer())
        workspace = new_triage_workspace(mode=TriageMode.INDEPENDENT)
        for record_id, _ in timestamps:
            workspace = prepare_workspace_ticket(
                workspace,
                result,
                None,
                None,
                record_id=record_id,
                excerpt="",
                complexity=TicketComplexity.INTERMEDIATE,
                guide=self.guide,
                applicable_rule_ids=("TRIAGE-UNCLEAR-001",),
                mock_suggestion=None,
                limits=TriageLimits(),
                ticket_id_factory=fixed_ticket_id(record_id),
            )
        return workspace

    def sorted_ids(
        self, workspace: TriageWorkspace, sort_by: str = "timestamp"
    ) -> list[str]:
        entries = filter_triage_entries(
            workspace, TriageFilter(), sort_by=sort_by
        )
        return [entry.ticket.ticket_id.removeprefix("workspace-") for entry in entries]

    def test_aware_offsets_order_by_instant_not_string(self) -> None:
        """String order and real-instant order disagree; instant order wins."""

        workspace = self.workspace_with(
            (
                # 13:00Z, but "08:00" sorts before "10:00" as raw text, so a
                # string sort places this later instant first.
                ("later-instant", "2026-07-01T08:00:00-05:00"),
                # 10:00Z, the genuinely earlier instant.
                ("earlier-instant", "2026-07-01T10:00:00+00:00"),
            )
        )
        self.assertEqual(
            self.sorted_ids(workspace), ["earlier-instant", "later-instant"]
        )

    def test_same_instant_across_offsets_keeps_original_order(self) -> None:
        """Two spellings of one instant tie and fall back to original order."""

        workspace = self.workspace_with(
            (
                # Both are 12:00Z, so only original order may separate them.
                # "07:00-05:00" sorts first as raw text, so a string sort would
                # reverse the arrival order instead of preserving it.
                ("added-first", "2026-07-01T12:00:00+00:00"),
                ("added-second", "2026-07-01T07:00:00-05:00"),
            )
        )
        self.assertEqual(self.sorted_ids(workspace), ["added-first", "added-second"])

    def test_naive_timestamps_order_by_wall_clock(self) -> None:
        """Timezone-unspecified values order by their stated clock value."""

        workspace = self.workspace_with(
            (
                ("naive-late", "2026-07-01T18:00:00"),
                ("naive-early", "2026-07-01T06:00:00"),
                ("naive-date-only", "2026-07-01"),
            )
        )
        self.assertEqual(
            self.sorted_ids(workspace),
            ["naive-date-only", "naive-early", "naive-late"],
        )

    def test_bucket_contract_orders_aware_then_naive_then_absent(self) -> None:
        """Aware, naive, and absent timestamps stay in separate ordered buckets."""

        workspace = self.workspace_with(
            (
                ("absent", ""),
                # Naive 1999 precedes every aware value by wall clock, but a
                # timezone-unspecified value is never merged into the aware
                # timeline, so it must still sort after every aware value.
                ("naive-1999", "1999-01-01T00:00:00"),
                ("aware-2030", "2030-01-01T00:00:00+00:00"),
                ("aware-2026", "2026-01-01T00:00:00+00:00"),
            )
        )
        self.assertEqual(
            self.sorted_ids(workspace),
            ["aware-2026", "aware-2030", "naive-1999", "absent"],
        )

    def test_absent_timestamps_sort_last_in_original_order(self) -> None:
        """Every absent timestamp sorts last while keeping its arrival order."""

        workspace = self.workspace_with(
            (
                ("absent-first", ""),
                ("aware", "2026-01-01T00:00:00+00:00"),
                ("absent-second", ""),
            )
        )
        self.assertEqual(
            self.sorted_ids(workspace),
            ["aware", "absent-first", "absent-second"],
        )

    def test_extreme_offset_does_not_crash_timestamp_sort(self) -> None:
        """A parsable extreme offset must not raise during sorting.

        `astimezone(UTC)` overflows on these values, so the sort key must
        compare aware datetimes without converting them.
        """

        workspace = self.workspace_with(
            (
                ("extreme-late", "9999-12-31T23:59:59-14:00"),
                ("extreme-early", "0001-01-01T00:00:00+14:00"),
                ("ordinary", "2026-01-01T00:00:00+00:00"),
            )
        )
        self.assertEqual(
            self.sorted_ids(workspace),
            ["extreme-early", "ordinary", "extreme-late"],
        )

    def test_other_sort_modes_are_unchanged(self) -> None:
        """Timestamp ordering must not leak into the other sort modes."""

        workspace = self.workspace_with(
            (
                ("third", "2026-01-01T00:00:00+00:00"),
                ("first", "2030-01-01T00:00:00+00:00"),
                ("second", ""),
            )
        )
        arrival = ["third", "first", "second"]
        self.assertEqual(self.sorted_ids(workspace, "original"), arrival)
        # No ticket is finalized, so urgency and status are uniform and both
        # modes must fall back to the untouched original order.
        self.assertEqual(self.sorted_ids(workspace, "urgency"), arrival)
        self.assertEqual(self.sorted_ids(workspace, "status"), arrival)

    def test_sorting_does_not_rewrite_stored_timestamp_values(self) -> None:
        """Sorting must not normalize, convert, or re-render stored values."""

        raw = (
            ("aware-offset", "2026-07-01T13:00:00-04:00"),
            ("naive", "2026-07-01T18:00:00"),
            ("absent", ""),
        )
        workspace = self.workspace_with(raw)
        before = {
            entry.ticket.ticket_id: entry.ticket.source_snapshot.source_timestamp
            for entry in workspace.entries
            if entry.ticket.source_snapshot is not None
        }
        filter_triage_entries(workspace, TriageFilter(), sort_by="timestamp")
        after = {
            entry.ticket.ticket_id: entry.ticket.source_snapshot.source_timestamp
            for entry in workspace.entries
            if entry.ticket.source_snapshot is not None
        }
        self.assertEqual(before, after)
        # The stored value keeps the user's own offset and is never made UTC.
        self.assertEqual(before["workspace-aware-offset"], "2026-07-01T13:00:00-04:00")
        self.assertEqual(before["workspace-naive"], "2026-07-01T18:00:00")
        self.assertEqual(before["workspace-absent"], "")

    def test_workspace_sort_help_states_the_bucket_contract(self) -> None:
        """The UI must not imply naive and aware times share one timeline."""

        markup = (TEMPLATES / "triage_workspace.html").read_text(encoding="utf-8")
        self.assertIn('aria-describedby="triage-sort-help"', markup)
        self.assertIn('id="triage-sort-help"', markup)
        self.assertIn("not converted or assumed to share one timeline", markup)


if __name__ == "__main__":
    unittest.main()
