"""The screens call the engine with the dataset that is on screen.

Inline configs are the Defense drafts. A stored dataset, not only the
in-memory dev corpus, has to open the command center, intelligence, and academy.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/live.db")
    from app.db import reset_engine
    from app.main import app

    reset_engine()
    return TestClient(app)


def _practice(client: TestClient) -> str:
    created = client.post("/api/v1/demo/reset")
    assert created.status_code == 200, created.text
    return str(created.json()["id"])


def _config(name: str) -> dict[str, object]:
    path = ROOT / "data" / "test" / "configs" / name
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_inline_config_matches_the_stored_config(client: TestClient) -> None:
    dataset_id = _practice(client)
    stored = client.post(
        "/api/v1/simulations",
        json={
            "dataset_id": dataset_id,
            "config_id": "trained",
            "runs": 2000,
            "seed": 42,
            "persist": False,
        },
    )
    assert stored.status_code == 200, stored.text
    inline = client.post(
        "/api/v1/simulations",
        json={
            "dataset_id": dataset_id,
            "config": _config("trained.yaml"),
            "runs": 2000,
            "seed": 42,
            "persist": False,
            "closed_form": True,
        },
    )
    assert inline.status_code == 200, inline.text
    assert inline.json()["aggregate"]["closed_form"] == pytest.approx(
        stored.json()["aggregate"]["closed_form"]
    )

    weaker = _config("trained.yaml")
    training = weaker["user_training"]
    assert isinstance(training, dict)
    training["level"] = "none"
    dropped = client.post(
        "/api/v1/simulations",
        json={
            "dataset_id": dataset_id,
            "config": weaker,
            "runs": 2000,
            "seed": 42,
            "persist": False,
            "closed_form": True,
        },
    )
    assert dropped.status_code == 200, dropped.text
    assert dropped.json()["aggregate"]["closed_form"] > inline.json()["aggregate"]["closed_form"]


def test_inline_comparison_returns_both_runs_and_the_diff(client: TestClient) -> None:
    dataset_id = _practice(client)
    compared = client.post(
        "/api/v1/comparisons",
        json={
            "dataset_id": dataset_id,
            "config_a": _config("untrained.yaml"),
            "config_b": _config("trained.yaml"),
            "runs": 1000,
            "seed": 42,
        },
    )
    assert compared.status_code == 200, compared.text
    body = compared.json()
    before = body["result_a"]["aggregate"]["closed_form"]
    after = body["result_b"]["aggregate"]["closed_form"]
    assert before > after
    assert body["relative_reduction"] == pytest.approx((before - after) / before)
    assert "modeled" in body["narrative"].lower()
    assert "9.59%" in body["narrative"]
    assert "3.82%" in body["narrative"]
    assert any(change["path"] == "user_training.level" for change in body["changes"])


def test_practice_dataset_opens_command_intelligence_and_academy(client: TestClient) -> None:
    dataset_id = _practice(client)
    simulated = client.post(
        "/api/v1/simulations",
        json={
            "dataset_id": dataset_id,
            "config_id": "untrained",
            "runs": 10000,
            "seed": 42,
            "persist": False,
        },
    )
    assert simulated.status_code == 200, simulated.text
    command = client.get(f"/api/v1/datasets/{dataset_id}/command")
    assert command.status_code == 200, command.text
    body = command.json()
    assert body["summary"]["email_count"] == 20
    assert body["summary"]["correct"] == 20
    assert body["before"]["closed_form"] == pytest.approx(
        simulated.json()["aggregate"]["closed_form"]
    )
    assert body["summary"]["relative_reduction"] == pytest.approx(0.6018489546161121, abs=1e-6)
    domains = client.get(f"/api/v1/datasets/{dataset_id}/domains")
    assert domains.status_code == 200, domains.text
    assert domains.json()["deceptive_links"]
    quiz = client.get(f"/api/v1/datasets/{dataset_id}/quiz", params={"n": 5, "seed": 42})
    assert quiz.status_code == 200, quiz.text
    assert len(quiz.json()) == 5


def test_stored_config_can_be_read_back(client: TestClient) -> None:
    _practice(client)
    loaded = client.get("/api/v1/configs/untrained")
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["config"]["user_training"]["level"] == "none"
    assert loaded.json()["config"]["name"] == "Untrained users (v1)"
