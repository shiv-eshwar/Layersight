"""Domain intelligence and the ad-hoc similarity checker."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.phase6_store import get_store
from layersight.phase6.models import DomainReport, SimilarityView

router = APIRouter(tags=["domains"])


class SimilarityRequest(BaseModel):
    candidate: str = Field(min_length=1)
    org_domains: list[str] = Field(default_factory=list)


@router.get("/datasets/{dataset_id}/domains", response_model=DomainReport)
def domains(dataset_id: str) -> DomainReport:
    report = get_store().domains(dataset_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"No dataset named {dataset_id}.")
    return report


@router.post("/domains/similarity", response_model=SimilarityView)
def similarity(body: SimilarityRequest) -> SimilarityView:
    return get_store().similarity(body.candidate, body.org_domains)
