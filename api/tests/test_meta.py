from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["engine_version"]


def test_meta_exposes_the_stated_assumptions() -> None:
    response = client.get("/api/v1/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "1"
    assumptions = body["assumptions"]
    assert assumptions["user_training"]["none"]["base"] == 0.30
    assert assumptions["user_training"]["advanced"]["base"] == 0.75
    titles = [item["title"] for item in assumptions["statements"]]
    assert "Layer independence" in titles
