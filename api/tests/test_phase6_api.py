"""Phase 6 HTTP: summary, similarity checker, and a recorded quiz."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


client = TestClient(app)


def test_paypa1_checker() -> None:
    response = client.post("/api/v1/domains/similarity", json={"candidate": "paypa1.com"})
    assert response.status_code == 200
    body = response.json()
    assert body["technique"] == "homoglyph"
    assert body["closest"] == "paypal.com"
    assert body["score"] == 0.98


def test_command_center_uses_the_dev_corpus() -> None:
    response = client.get("/api/v1/datasets/dev/command")
    assert response.status_code == 200
    body = response.json()
    summary = body["summary"]
    assert summary["email_count"] >= 20
    assert summary["accuracy"] is not None
    assert body["before"]["closed_form"] is not None
    assert body["after"]["closed_form"] is not None
    assert body["recommendation"]["detail"]
    assert body["note"].startswith("Figures are model estimates")


def test_empty_dataset_has_no_emails() -> None:
    response = client.get("/api/v1/datasets/empty/summary")
    assert response.status_code == 200
    assert response.json()["email_count"] == 0


def test_unknown_dataset_is_404() -> None:
    response = client.get("/api/v1/datasets/missing/command")
    assert response.status_code == 404


def test_quiz_records_a_catch_rate() -> None:
    questions = client.get("/api/v1/datasets/dev/quiz", params={"n": 10, "seed": 42})
    assert questions.status_code == 200
    payload = questions.json()
    assert len(payload) == 10
    assert "answer_id" not in payload[0]
    answers = [{"question_id": item["id"], "chosen": item["options"][0]["id"]} for item in payload]
    graded = client.post(
        "/api/v1/quiz/attempts",
        json={"dataset_id": "dev", "answers": answers, "n": 10, "seed": 42, "record": True},
    )
    assert graded.status_code == 200
    body = graded.json()
    assert body["total"] == 10
    assert body["recorded"] is True
    assert 0.02 <= body["catch_rate"] <= 0.98
    applied = client.post("/api/v1/quiz/user-layer", json={"dataset_id": "dev"})
    assert applied.status_code == 200
    assert applied.json()["source"] == "quiz"
    client.post("/api/v1/quiz/user-layer", json={"dataset_id": "dev", "reset": True})
