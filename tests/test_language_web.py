"""The frozen local web surface shows the same language warnings (synthetic data)."""

from __future__ import annotations

import io

from flask.testing import FlaskClient
from persistence.language_samples import LanguageGateway, mixed_language_csv

from social_text_intelligence.interface import create_app

CONFIG = {
    "TESTING": True,
    "MAX_BATCH_BYTES": 10_000,
    "MAX_BATCH_ROWS": 10,
    "MAX_TEXT_LENGTH": 200,
}


def client() -> FlaskClient:
    app = create_app(CONFIG, analysis_gateway=LanguageGateway())
    return app.test_client()


def uploaded_batch(c: FlaskClient) -> str:
    response = c.post(
        "/batch/upload",
        data={"file": (io.BytesIO(mixed_language_csv()), "mixed.csv")},
        content_type="multipart/form-data",
    )
    url = str(response.headers["Location"])
    c.post(url + "/analyze")
    return url


def test_direct_analysis_warns_for_a_text_in_another_language() -> None:
    c = client()

    page = c.post("/", data={"text": "bonjour tout le monde merci"})

    html = page.get_data(as_text=True)
    assert "Detected language: French (fr)" in html
    assert "still analysed" in html


def test_direct_analysis_does_not_warn_for_supported_language() -> None:
    c = client()

    html = c.post("/", data={"text": "Everything arrived on time."}).get_data(
        as_text=True
    )

    assert "Detected language: English (en)" in html
    assert "Warning:" not in html


def test_the_batch_results_summarise_the_language_check() -> None:
    c = client()
    url = uploaded_batch(c)

    html = c.get(url).get_data(as_text=True)

    assert "Language check: 3 of 5 analysed texts" in html
    assert "French (fr) 2" in html


def test_a_review_record_names_supplied_and_detected_language_apart() -> None:
    c = client()
    url = uploaded_batch(c)
    token = url.rsplit("/", 1)[-1]

    html = c.get(f"/batch/{token}/review/2").get_data(as_text=True)

    assert "Language supplied in the file" in html
    assert "Detected language: French (fr)" in html


def test_every_web_warning_says_warning_in_words() -> None:
    c = client()
    url = uploaded_batch(c)
    token = url.rsplit("/", 1)[-1]

    pages = {
        "batch": c.get(url).get_data(as_text=True),
        "review": c.get(f"/batch/{token}/review/2").get_data(as_text=True),
        "direct": c.post("/", data={"text": "bonjour tout le monde merci"}).get_data(
            as_text=True
        ),
    }

    for name, html in pages.items():
        assert "Warning: " in html, name


def test_the_batch_table_marks_each_row_and_the_insights_page_carries_the_caveat() -> (
    None
):
    c = client()
    url = uploaded_batch(c)
    token = url.rsplit("/", 1)[-1]

    table = c.get(url).get_data(as_text=True)
    insights = c.get(
        f"/batch/{token}/insights?grouping=language&groups=en"
    ).get_data(as_text=True)

    assert "Language check" in table and "⚠ French (fr)" in table
    assert "Language (as supplied in the file)" in insights
    assert "Language check: 3 of 5 analysed texts" in insights
    assert "2 of 3 analysed texts here are not confirmed" in insights
