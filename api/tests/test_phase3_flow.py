"""Upload, import, simulate, compare, and validate through the API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/phase3.db")
    from app.db import reset_engine
    from app.main import app

    reset_engine()
    return TestClient(app)


def test_end_to_end_flow(client: TestClient) -> None:
    files = [
        ("files", (path.name, path.read_bytes(), "message/rfc822"))
        for path in sorted((ROOT / "data" / "test" / "emails").glob("*.eml"))
    ]
    labels = (ROOT / "data" / "test" / "labels.csv").read_bytes()
    files.append(("labels", ("labels.csv", labels, "text/csv")))
    created = client.post("/api/v1/datasets", files=files, data={"name": "Official practice"})
    assert created.status_code == 201, created.text
    dataset_id = created.json()["id"]

    for name in ("untrained.yaml", "trained.yaml"):
        path = ROOT / "data" / "test" / "configs" / name
        imported = client.post(
            "/api/v1/configs/import",
            files=[("file", (path.name, path.read_bytes(), "application/yaml"))],
        )
        assert imported.status_code == 201, imported.text

    simulated = client.post(
        "/api/v1/simulations",
        json={
            "dataset_id": dataset_id,
            "config_id": "untrained",
            "runs": 2000,
            "seed": 42,
            "persist": True,
        },
    )
    assert simulated.status_code == 200, simulated.text
    simulation = simulated.json()
    assert simulation["runs"] == 2000
    assert simulation["seed"] == 42
    assert simulation["aggregate"]["email_count"] > 0
    assert 0.0 < simulation["aggregate"]["closed_form"] < 1.0
    low, high = simulation["aggregate"]["ci95"]
    assert low <= simulation["aggregate"]["pass_rate"] <= high
    stored = client.get(f"/api/v1/simulations/{simulation['id']}")
    assert stored.status_code == 200
    assert stored.json()["aggregate"]["closed_form"] == simulation["aggregate"]["closed_form"]

    compared = client.post(
        "/api/v1/comparisons",
        json={
            "dataset_id": dataset_id,
            "config_a_id": "untrained",
            "config_b_id": "trained",
            "runs": 2000,
            "seed": 42,
        },
    )
    assert compared.status_code == 200, compared.text
    comparison = compared.json()
    assert "modeled" in comparison["narrative"].lower()
    assert comparison["relative_reduction"] > 0
    assert comparison["per_email"]

    report = client.get(f"/api/v1/datasets/{dataset_id}/validation", params={"runs": 500})
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["total"] == 20
    assert body["correct"] >= 18
    assert body["accuracy"] >= 0.9

    advice = client.post(
        "/api/v1/recommendations",
        json={"dataset_id": dataset_id, "config_id": "untrained"},
    )
    assert advice.status_code == 200, advice.text
    assert advice.json()["recommendations"]
    assert advice.json()["sensitivity"]

    docs = client.get("/docs")
    assert docs.status_code == 200
    spec = client.get("/openapi.json")
    paths = spec.json()["paths"]
    for route in (
        "/api/v1/datasets",
        "/api/v1/configs/import",
        "/api/v1/simulations",
        "/api/v1/comparisons",
        "/api/v1/recommendations",
        "/api/v1/datasets/{dataset_id}/validation",
    ):
        assert route in paths
