from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTIONNAIRE = ROOT / "manual-qa" / "manual_review_questionnaire.html"


class IdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del tag
        for name, value in attrs:
            if name == "id" and value is not None:
                self.ids.append(value)


def test_manual_qa_questionnaire_has_stable_navigation_and_valid_ids() -> None:
    source = QUESTIONNAIRE.read_text(encoding="utf-8")
    parser = IdCollector()
    parser.feed(source)
    parser.close()

    assert len(parser.ids) == len(set(parser.ids))
    assert 'id="module-nav"' in source
    assert 'id="sections"' in source
    assert 'id="overall"' in source
    assert 'element("nav", "section-actions")' in source
    assert 'sessionNavTitle: "Session navigation"' in source
    assert 'previousSession: "\u2190 Previous session"' in source
    assert 'nextSession: "Next session \u2192"' in source
    assert "sample-data/direct_text_cases.md" in source
    assert "sample-data/review_insights_workflow.csv" in source


def test_manual_qa_results_are_repository_ignored() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "manual-qa/results/" in gitignore
