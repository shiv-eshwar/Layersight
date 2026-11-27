"""Dataset, investigation, and report routes used by the core UI."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from app.db import session
from app.services import (
    APIError,
    compare_configs,
    email_detail,
    get_config,
    import_config_text,
    ingest,
    list_configs,
    list_datasets,
    list_emails,
    load_run,
    override_vector,
    parse_config,
    recommend_dataset,
    report_csv,
    reset_demo,
    simulate_dataset,
    validation_report,
)

router = APIRouter(prefix="/api/v1")


def _fail(exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": exc.title,
            "status": exc.status,
            "detail": exc.detail,
            "fields": exc.fields,
        },
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


@router.get("/configs/{config_id}")
def one_config(config_id: str) -> JSONResponse:
    db = next(session())
    try:
        return JSONResponse(get_config(db, config_id))
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
def emails(
    dataset_id: str, q: str = "", prediction: str = "all", sort: str = "-risk"
) -> JSONResponse:
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
            email_detail(
                db, email_id, baseline_id=baseline, comparison_id=comparison, runs=runs, seed=seed
            )
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
            validation_report(
                db, dataset_id, baseline_id=baseline, comparison_id=comparison, runs=runs, seed=seed
            )
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
        body = validation_report(
            db, dataset_id, baseline_id=baseline, comparison_id=comparison, runs=runs, seed=seed
        )
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
        body = validation_report(
            db, dataset_id, baseline_id=baseline, comparison_id=comparison, runs=runs, seed=seed
        )
    except APIError as exc:
        return _fail(exc)
    finally:
        db.close()
    return Response(
        report_csv(body),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{dataset_id}.csv"'},
    )


class SimulationBody(BaseModel):
    dataset_id: str
    config_id: str | None = None
    config: dict[str, object] | None = None
    runs: int = Field(default=10000, ge=1, le=100_000)
    seed: int = 42
    persist: bool = True
    closed_form: bool = False


class ComparisonBody(BaseModel):
    dataset_id: str
    config_a_id: str | None = None
    config_b_id: str | None = None
    config_a: dict[str, object] | None = None
    config_b: dict[str, object] | None = None
    runs: int = Field(default=10000, ge=1, le=100_000)
    seed: int = 42


class RecommendationBody(BaseModel):
    dataset_id: str
    config_id: str | None = None
    config: dict[str, object] | None = None


class VectorBody(BaseModel):
    attack_vector: str


@router.post("/configs/import")
def import_config(file: UploadFile = File(...)) -> JSONResponse:
    text = file.file.read().decode("utf-8", errors="replace")
    db = next(session())
    try:
        return JSONResponse(
            import_config_text(db, file.filename or "config.yaml", text), status_code=201
        )
    except APIError as exc:
        return _fail(exc)
    finally:
        db.close()


@router.post("/simulations")
def simulations(body: SimulationBody) -> JSONResponse:
    db = next(session())
    try:
        config = parse_config(body.config) if body.config is not None else None
        return JSONResponse(
            simulate_dataset(
                db,
                body.dataset_id,
                body.config_id,
                runs=body.runs,
                seed=body.seed,
                persist=body.persist,
                config=config,
                closed_form_only=body.closed_form,
            )
        )
    except APIError as exc:
        return _fail(exc)
    finally:
        db.close()


@router.get("/simulations/{run_id}")
def simulation(run_id: str) -> JSONResponse:
    db = next(session())
    try:
        return JSONResponse(load_run(db, run_id))
    except APIError as exc:
        return _fail(exc)
    finally:
        db.close()


@router.post("/comparisons")
def comparisons(body: ComparisonBody) -> JSONResponse:
    db = next(session())
    try:
        config_a = parse_config(body.config_a) if body.config_a is not None else None
        config_b = parse_config(body.config_b) if body.config_b is not None else None
        return JSONResponse(
            compare_configs(
                db,
                body.dataset_id,
                body.config_a_id,
                body.config_b_id,
                runs=body.runs,
                seed=body.seed,
                config_a=config_a,
                config_b=config_b,
            )
        )
    except APIError as exc:
        return _fail(exc)
    finally:
        db.close()


@router.post("/recommendations")
def recommendations(body: RecommendationBody) -> JSONResponse:
    db = next(session())
    try:
        config = parse_config(body.config) if body.config is not None else None
        return JSONResponse(recommend_dataset(db, body.dataset_id, body.config_id, config))
    except APIError as exc:
        return _fail(exc)
    finally:
        db.close()


@router.patch("/emails/{email_id}")
def patch_email(email_id: str, body: VectorBody) -> JSONResponse:
    db = next(session())
    try:
        return JSONResponse(override_vector(db, email_id, body.attack_vector))
    except APIError as exc:
        return _fail(exc)
    finally:
        db.close()
