"""Upload the practice set and require at least 18 of 20 correct."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/phase4.db")
    from app.db import reset_engine
    from app.main import app

    reset_engine()
    return TestClient(app)


def test_practice_set_scores_at_least_18_of_20(client: TestClient) -> None:
    files = []
    for path in sorted((ROOT / "data" / "test" / "emails").glob("*.eml")):
        files.append(("files", (path.name, path.read_bytes(), "message/rfc822")))
    labels = (ROOT / "data" / "test" / "labels.csv").read_bytes()
    files.append(("labels", ("labels.csv", labels, "text/csv")))
    created = client.post("/api/v1/datasets", files=files, data={"name": "Practice"})
    assert created.status_code == 201, created.text
    dataset_id = created.json()["id"]
    report = client.get(f"/api/v1/datasets/{dataset_id}/validation?runs=1000")
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["total"] == 20
    assert body["correct"] >= 18
    assert body["accuracy"] >= 0.9


def test_zip_rejects_path_traversal(client: TestClient) -> None:
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../escape.eml", "From: a@b.test\n\nHello\n")
    response = client.post(
        "/api/v1/datasets",
        files=[("files", ("bad.zip", buffer.getvalue(), "application/zip"))],
    )
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
