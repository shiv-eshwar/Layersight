"""Persistence for datasets, analyses, configs, and simulation runs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Organization(Base):
    __tablename__ = "organization"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))


class Dataset(Base):
    __tablename__ = "dataset"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("organization.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(32), default="upload")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Email(Base):
    __tablename__ = "email"
    __table_args__ = (UniqueConstraint("dataset_id", "sha256", name="uq_email_dataset_sha"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(300))
    sha256: Mapped[str] = mapped_column(String(64))
    raw_text: Mapped[str] = mapped_column(Text)
    label: Mapped[str | None] = mapped_column(String(16), nullable=True)
    subject: Mapped[str] = mapped_column(Text, default="")
    from_address: Mapped[str] = mapped_column(Text, default="")


class Analysis(Base):
    __tablename__ = "analysis"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email_id: Mapped[str] = mapped_column(ForeignKey("email.id", ondelete="CASCADE"), index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    engine_version: Mapped[str] = mapped_column(String(32))
    weights_hash: Mapped[str] = mapped_column(String(64))
    risk_score: Mapped[float]
    label: Mapped[str] = mapped_column(String(16))
    band: Mapped[str] = mapped_column(String(16))
    attack_vector: Mapped[str] = mapped_column(String(32))
    analysis: Mapped[dict[str, Any]] = mapped_column(JSON)
    presentation: Mapped[dict[str, Any]] = mapped_column(JSON)


class LayerConfigRow(Base):
    __tablename__ = "layer_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("organization.id", ondelete="CASCADE"))
    family_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(Integer)
    body: Mapped[dict[str, Any]] = mapped_column(JSON)
    source_filename: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SimulationRun(Base):
    __tablename__ = "simulation_run"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset.id", ondelete="CASCADE"), index=True)
    config_id: Mapped[str | None] = mapped_column(
        ForeignKey("layer_config.id", ondelete="SET NULL"), nullable=True
    )
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    runs: Mapped[int] = mapped_column(Integer)
    seed: Mapped[int] = mapped_column(Integer)
    engine_version: Mapped[str] = mapped_column(String(32))
    results: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Comparison(Base):
    __tablename__ = "comparison"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset.id", ondelete="CASCADE"), index=True)
    run_a_id: Mapped[str | None] = mapped_column(
        ForeignKey("simulation_run.id", ondelete="SET NULL"), nullable=True
    )
    run_b_id: Mapped[str | None] = mapped_column(
        ForeignKey("simulation_run.id", ondelete="SET NULL"), nullable=True
    )
    summary: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class QuizQuestion(Base):
    __tablename__ = "quiz_question"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    email_id: Mapped[str] = mapped_column(ForeignKey("email.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list[dict[str, str]]] = mapped_column(JSON)
    answer: Mapped[str] = mapped_column(String(200))
    explanation: Mapped[str] = mapped_column(Text)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempt"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("quiz_question.id", ondelete="CASCADE"))
    participant: Mapped[str] = mapped_column(String(200))
    chosen: Mapped[str] = mapped_column(String(200))
    correct: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
