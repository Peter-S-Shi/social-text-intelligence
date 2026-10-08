"""Desktop composition root (Qt-free): wires the ports to their adapters.

The desktop layer reaches models only through ``ModelProvisioning`` and the shared
``AnalysisGate``, and projects only through the repository port. It never touches
SQLite, Transformers, or PyTorch directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..application.insights_workflow import InsightsWorkflow
from ..application.model_provisioning import (
    ModelProvisioning,
    build_provisioned_analysis_service,
)
from ..application.project_workflow import CsvLimits, ProjectWorkflow
from ..application.projects import PersistentProjectRepository
from ..application.review_workflow import ReviewWorkflow
from ..application.settings import AnalysisGateway, AppSettings
from ..application.use_cases import ApplicationUseCases
from ..contracts import AnalysisReport
from ..infrastructure.app_data import AppDataLocations
from ..infrastructure.model_store import local_model_provisioner
from ..infrastructure.sqlite_projects import SqliteProjectRepository
from .analysis import AnalysisPageController
from .controller import JobRunner, ProvisioningController
from .gate import AnalysisGate
from .insights import InsightsController
from .projects import ProjectsController
from .review import ReviewController


@dataclass(frozen=True, slots=True)
class DesktopServices:
    locations: AppDataLocations
    settings: AppSettings
    provisioning: ModelProvisioning
    gate: AnalysisGate
    projects: PersistentProjectRepository
    workflow: ProjectWorkflow
    reviews: ReviewWorkflow
    insights: InsightsWorkflow
    use_cases: ApplicationUseCases


def build_desktop_services(
    locations: AppDataLocations,
    *,
    settings: AppSettings | None = None,
    provisioning: ModelProvisioning | None = None,
    analysis: AnalysisGateway | None = None,
) -> DesktopServices:
    """Production wiring by default; tests inject a provisioner and a gateway."""

    settings = settings or AppSettings()
    provisioning = provisioning or local_model_provisioner(locations)
    inner = analysis or build_provisioned_analysis_service(settings, provisioning)
    gate = AnalysisGate(inner)
    projects = SqliteProjectRepository(locations)
    return DesktopServices(
        locations=locations,
        settings=settings,
        provisioning=provisioning,
        gate=gate,
        projects=projects,
        workflow=ProjectWorkflow(projects, gate, CsvLimits.from_settings(settings)),
        reviews=ReviewWorkflow(projects),
        insights=InsightsWorkflow(projects),
        use_cases=ApplicationUseCases(projects, gate),
    )


def build_provisioning_controller(
    services: DesktopServices, runner: JobRunner
) -> ProvisioningController:
    """The controller whose Verify results feed the H2 session gate."""

    controller = ProvisioningController(services.provisioning, runner)
    controller.add_verify_observer(services.gate.note_verify_result)
    return controller


def build_analysis_controller(
    services: DesktopServices, runner: JobRunner
) -> AnalysisPageController:
    limit = services.settings.max_text_length

    def analyze(text: str) -> AnalysisReport:
        return services.use_cases.analyze_text(text, max_text_length=limit)

    return AnalysisPageController(analyze, runner)


def build_projects_controller(
    services: DesktopServices, runner: JobRunner
) -> ProjectsController:
    return ProjectsController(
        services.workflow,
        runner,
        max_file_bytes=services.settings.max_batch_bytes,
    )


def build_review_controller(
    services: DesktopServices, runner: JobRunner
) -> ReviewController:
    return ReviewController(services.reviews, runner)


def build_insights_controller(
    services: DesktopServices, runner: JobRunner
) -> InsightsController:
    return InsightsController(services.insights, runner)
