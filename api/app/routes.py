"""Dataset, investigation, and report routes used by the core UI."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse, Response

from app.db import session
from app.services import (
    APIError,
    email_detail,
    ingest,
    list_configs,
    list_datasets,
    list_emails,
    report_csv,
    reset_demo,
    validation_report,
)

router = APIRouter(prefix="/api/v1")


def _fail(exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        media_type="application/problem+json",
        content={"type": "about:blank", "title": exc.title, "status": exc.status, "detail": exc.detail, "fields": exc.fields},
    )


@router.get("/configs")
def configs() -> JSONResponse:
    db = next(session())
    try:
        return JSONResponse(list_configs(db))
    except APIError as exc:
        return _fail(exc)
    finally:
        db.close()


@router.get("/datasets")
def datasets() -> JSONResponse:
    db = next(session())
    try:
        return JSONResponse(list_datasets(db))
    finally:
        db.close()


@router.post("/datasets")
def create_dataset(
    files: list[UploadFile] = File(...),
    labels: UploadFile | None = File(None),
    name: str | None = Form(None),
) -> JSONResponse:
    payload: list[tuple[str, bytes]] = []
    for item in files:
        payload.append((item.filename or "message.eml", item.file.read()))
    label_text = None
    if labels is not None:
        label_text = labels.file.read().decode("utf-8", errors="replace")
    db = next(session())
    try:
        return JSONResponse(ingest(db, payload, label_text, name), status_code=201)
    except APIError as exc:
        return _fail(exc)
    finally:
        db.close()


@router.post("/demo/reset")
def demo_reset() -> JSONResponse:
    db = next(session())
    try:
        return JSONResponse(reset_demo(db))
    except APIError as exc:
        return _fail(exc)
    finally:
        db.close()


@router.get("/datasets/{dataset_id}/emails")
def emails(dataset_id: str, q: str = "", prediction: str = "all", sort: str = "-risk") -> JSONResponse:
    db = next(session())
    try:
        return JSONResponse(list_emails(db, dataset_id, q=q, prediction=prediction, sort=sort))
    except APIError as exc:
        return _fail(exc)
    finally:
        db.close()


@router.get("/emails/{email_id}")
def one_email(
    email_id: str,
    baseline: str | None = None,
    comparison: str | None = None,
    runs: int = 10000,
    seed: int = 42,
) -> JSONResponse:
    db = next(session())
    try:
        return JSONResponse(
            email_detail(db, email_id, baseline_id=baseline, comparison_id=comparison, runs=runs, seed=seed)
        )
    except APIError as exc:
        return _fail(exc)
    finally:
        db.close()


@router.get("/datasets/{dataset_id}/validation")
def validation(
    dataset_id: str,
    baseline: str | None = None,
    comparison: str | None = None,
    runs: int = 10000,
    seed: int = 42,
) -> JSONResponse:
    db = next(session())
    try:
        return JSONResponse(
            validation_report(db, dataset_id, baseline_id=baseline, comparison_id=comparison, runs=runs, seed=seed)
        )
    except APIError as exc:
        return _fail(exc)
    finally:
        db.close()


@router.get("/datasets/{dataset_id}/report.json")
def report_json(
    dataset_id: str,
    baseline: str | None = None,
    comparison: str | None = None,
    runs: int = 10000,
    seed: int = 42,
) -> JSONResponse:
    db = next(session())
    try:
        body = validation_report(db, dataset_id, baseline_id=baseline, comparison_id=comparison, runs=runs, seed=seed)
    except APIError as exc:
        return _fail(exc)
    finally:
        db.close()
    return JSONResponse(
        body,
        headers={"Content-Disposition": f'attachment; filename="{dataset_id}.json"'},
    )


@router.get("/datasets/{dataset_id}/report.csv")
def report_csv_route(
    dataset_id: str,
    baseline: str | None = None,
    comparison: str | None = None,
    runs: int = 10000,
    seed: int = 42,
) -> Response:
    db = next(session())
    try:
        body = validation_report(db, dataset_id, baseline_id=baseline, comparison_id=comparison, runs=runs, seed=seed)
    except APIError as exc:
        return _fail(exc)
    finally:
        db.close()
    return Response(
        report_csv(body),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{dataset_id}.csv"'},
    )
