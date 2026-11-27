"""Academy questions, attempts, and the quiz catch rate."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.phase6_store import get_store
from layersight.phase6.models import AnswerIn, QuizGrade, QuizQuestionView, UserLayerUpdate

router = APIRouter(tags=["quiz"])


class AttemptRequest(BaseModel):
    dataset_id: str
    participant: str = "local"
    n: int = Field(default=10, ge=1, le=30)
    seed: int = 42
    answers: list[AnswerIn]
    record: bool = False


class UserLayerRequest(BaseModel):
    dataset_id: str
    reset: bool = False


@router.get("/datasets/{dataset_id}/quiz", response_model=list[QuizQuestionView])
def quiz(dataset_id: str, n: int = 10, seed: int = 42) -> list[QuizQuestionView]:
    questions = get_store().questions(dataset_id, n=n, seed=seed)
    if questions is None:
        raise HTTPException(status_code=404, detail=f"No dataset named {dataset_id}.")
    return questions


@router.post("/quiz/attempts", response_model=QuizGrade)
def attempts(body: AttemptRequest) -> QuizGrade:
    result = get_store().grade(body.dataset_id, body.answers, body.n, body.seed, body.record)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No dataset named {body.dataset_id}.")
    return result


@router.post("/quiz/user-layer", response_model=UserLayerUpdate)
def user_layer(body: UserLayerRequest) -> UserLayerUpdate:
    updated = get_store().apply_user_layer(body.dataset_id, body.reset)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"No dataset named {body.dataset_id}.")
    if not body.reset and updated.catch_rate is None:
        raise HTTPException(
            status_code=409,
            detail="Finish a recorded quiz before using its accuracy as the user-layer catch rate.",
        )
    return updated
