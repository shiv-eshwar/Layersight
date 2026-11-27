"""Command center summary."""

from fastapi import APIRouter, HTTPException

from app.services.phase6_store import get_store
from layersight.phase6.models import CommandCenter, DatasetSummary

router = APIRouter(tags=["command"])


@router.get("/datasets")
def list_datasets() -> list[dict[str, object]]:
    return get_store().list_datasets()


@router.get("/datasets/{dataset_id}/summary", response_model=DatasetSummary)
def summary(dataset_id: str) -> DatasetSummary:
    report = _report(dataset_id)
    return report.summary


@router.get("/datasets/{dataset_id}/command", response_model=CommandCenter)
def command(dataset_id: str) -> CommandCenter:
    return _report(dataset_id)


def _report(dataset_id: str) -> CommandCenter:
    report = get_store().command(dataset_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"No dataset named {dataset_id}.")
    return report
