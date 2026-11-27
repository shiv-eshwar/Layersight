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
    store = get_store()
    if store.get(dataset_id) is not None:
        report = store.command(dataset_id)
        if report is not None:
            return report
    from app.services.live_command import command_for_dataset

    report = command_for_dataset(dataset_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"No dataset named {dataset_id}.")
    return report
