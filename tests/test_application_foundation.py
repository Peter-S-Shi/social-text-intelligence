"""Public application seams for the V2 foundation."""

from dataclasses import replace

import pytest

from social_text_intelligence.application.projects import (
    BatchWorkspace,
    InMemoryProjectRepository,
    ProjectRepository,
    WorkspaceMutationConflict,
)
from social_text_intelligence.application.settings import (
    AppSettings,
    build_analysis_service,
)
from social_text_intelligence.application.use_cases import ApplicationUseCases
from social_text_intelligence.contracts import (
    AnalysisReport,
    EmotionLabel,
    NormalizedTextInput,
    SentimentLabel,
)
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import AnalysisService, LazyAnalysisService
from social_text_intelligence.services.batch import (
    BatchCancelled,
    BatchPreview,
    BatchProgress,
    analyze_batch,
    inspect_csv_upload,
    prepare_csv_batch,
)


class FailingGateway:
    initialized = True

    def analyze(self, record: NormalizedTextInput) -> AnalysisReport:
        raise RuntimeError("synthetic failure")


def one_row_preview() -> BatchPreview:
    pending = inspect_csv_upload(b"text\nA synthetic example.\n", max_bytes=1000)
    return prepare_csv_batch(
        pending, text_column="text", max_rows=10, max_text_length=100
    )


def deterministic_gateway() -> LazyAnalysisService:
    return LazyAnalysisService(
        lambda: AnalysisService(
            sentiment_provider=DeterministicSentimentProvider(SentimentLabel.POSITIVE),
            emotion_provider=DeterministicEmotionProvider(EmotionLabel.GRATITUDE),
        )
    )


def test_repository_port_keeps_the_current_workspace_during_atomic_mutation() -> None:
    repository: ProjectRepository = InMemoryProjectRepository()
    token = repository.create(BatchWorkspace())
    repository.mutate(token, lambda current: replace(current, pending=None))
    lease = repository.begin_analysis(token)
    assert lease is not None
    with pytest.raises(WorkspaceMutationConflict):
        repository.mutate(token, lambda current: current)
    assert repository.cancel_analysis(lease)
    assert repository.get(token) == BatchWorkspace()


def test_application_exposes_shared_safe_error_mapping() -> None:
    from social_text_intelligence.contracts.errors import ProviderError

    use_cases = ApplicationUseCases(InMemoryProjectRepository(), None)
    error = ProviderError(
        provider="test", code="missing_model_dependencies", message="private detail"
    )
    assert "Install the model extras" in use_cases.safe_error(error)
    assert "private detail" not in use_cases.safe_error(error)


def test_settings_keep_model_construction_lazy_and_validate_request_capacity() -> None:
    gateway = build_analysis_service(AppSettings())
    assert gateway.initialized is False
    with pytest.raises(ValueError, match="greater than MAX_BATCH_BYTES"):
        AppSettings(max_request_bytes=100, max_batch_bytes=100)


def test_batch_progress_and_cancellation_are_public_contracts() -> None:
    assert BatchProgress(completed=1, total=2).fraction == 0.5
    assert issubclass(BatchCancelled, Exception)


def test_batch_progress_reports_processed_rows_even_when_analysis_fails() -> None:
    observed: list[BatchProgress] = []
    result = analyze_batch(
        one_row_preview(), FailingGateway(), progress=observed.append
    )
    assert result.aggregates.failed_count == 1
    assert observed == [BatchProgress(completed=1, total=1)]


def test_cancelled_analysis_releases_lease_without_committing() -> None:
    repository = InMemoryProjectRepository()
    token = repository.create(BatchWorkspace(preview=one_row_preview()))
    use_cases = ApplicationUseCases(repository, FailingGateway())
    with pytest.raises(BatchCancelled):
        use_cases.analyze_workspace(token, cancelled=lambda: True)
    workspace = repository.get(token)
    assert workspace is not None and workspace.result is None
    lease = repository.begin_analysis(token)
    assert lease is not None
    assert repository.cancel_analysis(lease)


def test_cancellation_after_last_progress_event_still_prevents_commit() -> None:
    repository = InMemoryProjectRepository()
    token = repository.create(BatchWorkspace(preview=one_row_preview()))
    cancelled = False

    def progress(_event: BatchProgress) -> None:
        nonlocal cancelled
        cancelled = True

    use_cases = ApplicationUseCases(repository, FailingGateway())
    with pytest.raises(BatchCancelled):
        use_cases.analyze_workspace(
            token, progress=progress, cancelled=lambda: cancelled
        )
    workspace = repository.get(token)
    assert workspace is not None and workspace.result is None


def test_application_batch_review_and_export_work_without_flask() -> None:
    repository = InMemoryProjectRepository()
    use_cases = ApplicationUseCases(repository, deterministic_gateway())
    token = use_cases.upload_batch(
        b"record_id,text,topic\ncase-1,A synthetic example.,shipping\n",
        max_bytes=1000,
        max_rows=10,
        max_text_length=100,
    )
    assert use_cases.analyze_workspace(token) is True
    assert (
        use_cases.review_index(
            token,
            review_filter="all",
            sentiment_filter="all",
            emotion_filter="all",
        )
        == 1
    )
    assert (
        use_cases.save_review(
            token,
            1,
            action="accept_both",
            values={"review_note": "synthetic note"},
            secondary_emotions=(),
            review_filter="all",
            sentiment_filter="all",
            emotion_filter="all",
        )
        == 1
    )
    workspace = repository.get(token)
    assert workspace is not None
    assert "synthetic note" in use_cases.export_reviews(workspace, include_native=False)
    insight = use_cases.resolve_insights(
        token, workspace, {}, (), (), comparison=False
    )
    assert insight is not None
    assert insight.selection.groups == ("shipping",)
    assert insight.error_message is None
