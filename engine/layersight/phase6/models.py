"""Response shapes for the command center, intelligence, and academy."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

QuizKind = Literal["phish_or_legit", "most_suspicious", "link_destination"]
UserLayerSource = Literal["config", "quiz"]


class DomainRow(BaseModel):
    domain: str
    closest_brand: str | None = None
    similarity: float = Field(ge=0, le=1)
    technique: str
    occurrences: int = Field(ge=0)
    email_ids: list[str]
    diff: str = ""
    sentence: str


class DeceptiveLink(BaseModel):
    email_id: str
    subject: str
    visible_text: str
    href: str
    visible_domain: str
    real_domain: str
    closest_brand: str | None = None
    similarity: float = Field(ge=0, le=1)
    technique: str
    sentence: str


class DomainReport(BaseModel):
    dataset_id: str
    domains: list[DomainRow]
    deceptive_links: list[DeceptiveLink]


class SimilarityView(BaseModel):
    candidate: str
    score: float = Field(ge=0, le=1)
    closest: str | None = None
    technique: str
    diff: str = ""
    sentence: str
    legitimate: bool


class UncertaintyBand(BaseModel):
    p05: float
    p50: float
    p95: float
    kappa: float


class FunnelStep(BaseModel):
    layer: str
    label: str
    entered: int = Field(ge=0)
    stopped: int = Field(ge=0)


class Outlook(BaseModel):
    name: str
    pass_rate: float | None = None
    blocked_rate: float | None = None
    passed: int | None = None
    blocked: int | None = None
    runs: int = Field(ge=1)
    closed_form: float | None = None
    funnel: list[FunnelStep]
    uncertainty: UncertaintyBand | None = None


class RecommendationView(BaseModel):
    id: str
    title: str
    detail: str
    layer: str
    absolute_reduction: float
    relative_reduction: float
    vectors_helped: list[str]


class ThreatRow(BaseModel):
    email_id: str
    subject: str
    sender: str
    risk_score: float
    band: str
    label: str
    attack_vector: str
    top_evidence: str | None = None


class BrandRow(BaseModel):
    brand: str
    occurrences: int = Field(ge=0)
    technique: str
    similarity: float


class DatasetSummary(BaseModel):
    dataset_id: str
    name: str
    email_count: int = Field(ge=0)
    phishing_count: int | None = None
    genuine_count: int | None = None
    accuracy: float | None = None
    correct: int | None = None
    labeled: int | None = None
    pass_rate_before: float | None = None
    pass_rate_after: float | None = None
    relative_reduction: float | None = None


class CommandCenter(BaseModel):
    summary: DatasetSummary
    before: Outlook
    after: Outlook
    trained_pass_rate: float | None = None
    recommendation: RecommendationView | None = None
    threats: list[ThreatRow]
    brands: list[BrandRow]
    user_layer_source: UserLayerSource
    user_catch_rate: float | None = None
    engine_version: str
    seed: int
    note: str


class QuizOption(BaseModel):
    id: str
    text: str


class QuizQuestionView(BaseModel):
    id: str
    email_id: str
    kind: QuizKind
    prompt: str
    subject: str
    sender: str
    excerpt: str
    options: list[QuizOption]


class QuizQuestion(QuizQuestionView):
    answer_id: str
    explanation: str


class AnswerIn(BaseModel):
    question_id: str
    chosen: str


class AnswerResult(BaseModel):
    question_id: str
    chosen: str
    correct: bool
    correct_option_id: str
    explanation: str


class QuizGrade(BaseModel):
    dataset_id: str
    correct: int = Field(ge=0)
    total: int = Field(ge=0)
    accuracy: float = Field(ge=0, le=1)
    catch_rate: float = Field(ge=0, le=1)
    weak_areas: list[str]
    results: list[AnswerResult]
    recorded: bool


class UserLayerUpdate(BaseModel):
    dataset_id: str
    catch_rate: float | None = None
    source: UserLayerSource
    accuracy: float | None = None
    reset: bool = False
