"""Accuracy, confusion, and the explanation of each mistake. Labels stay in this module."""

from __future__ import annotations

import csv
from pathlib import Path

from pydantic import BaseModel, Field

from layersight.models import Evidence
from layersight.refs import weights
from layersight.scoring.analyze import analyze_email


class EmailRow(BaseModel):
    filename: str
    subject: str
    actual: str | None
    predicted: str
    risk_score: float
    band: str
    attack_vector: str
    correct: bool | None
    top_evidence: str | None
    distance_to_threshold: float
    evidence: list[Evidence] = Field(default_factory=list)
    explanation: str | None = None


class Confusion(BaseModel):
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0


class ValidationReport(BaseModel):
    total: int
    labeled: int
    actual_phishing: int
    actual_genuine: int
    predicted_phishing: int
    predicted_genuine: int
    correct: int | None
    accuracy: float | None
    precision: float | None
    recall: float | None
    f1: float | None
    false_positive_rate: float | None
    false_negative_rate: float | None
    confusion: Confusion
    per_email: list[EmailRow]
    misclassifications: list[EmailRow]
    engine_version: str
    weights_hash: str
    threshold: float


def load_labels(path: Path) -> dict[str, str]:
    labels: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            filename = (row.get("filename") or row.get("file") or "").strip()
            label = (row.get("label") or "").strip().lower()
            if filename and label in {"phishing", "genuine"}:
                labels[filename] = label
    return labels


def read_messages(directory: Path) -> list[tuple[str, str]]:
    files = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in {".eml", ".txt"}
    )
    return [(path.name, path.read_text(encoding="utf-8", errors="replace")) for path in files]


def validate_messages(
    messages: list[tuple[str, str]],
    labels: dict[str, str],
    org_domains: list[str] | None = None,
) -> ValidationReport:
    table = weights()
    rows: list[EmailRow] = []
    version = ""
    for filename, raw in messages:
        bundle = analyze_email(raw, org_domains)
        version = bundle.analysis.engine_version
        actual = labels.get(filename)
        predicted = bundle.analysis.label
        top = next((item.title for item in bundle.analysis.evidence if item.contribution > 0), None)
        distance = abs(bundle.analysis.risk_score - table.threshold)
        correct = None if actual is None else actual == predicted
        explanation = None
        if actual is not None and actual != predicted:
            side = "below" if bundle.analysis.risk_score < table.threshold else "above"
            details = "; ".join(item.detail for item in bundle.analysis.evidence[:3])
            explanation = (
                f"Labeled {actual}, predicted {predicted}. "
                f"Risk {bundle.analysis.risk_score:.2f} is {distance:.2f} {side} "
                f"the {table.threshold:.2f} threshold. {details}"
            )
        rows.append(
            EmailRow(
                filename=filename,
                subject=bundle.presentation.subject,
                actual=actual,
                predicted=predicted,
                risk_score=bundle.analysis.risk_score,
                band=bundle.analysis.band,
                attack_vector=bundle.analysis.attack_vector,
                correct=correct,
                top_evidence=top,
                distance_to_threshold=distance,
                evidence=bundle.analysis.evidence,
                explanation=explanation,
            )
        )
    return _summarize(rows, version, table.digest, table.threshold)


def validate_directory(directory: Path, labels_path: Path, org_domains: list[str] | None = None) -> ValidationReport:
    return validate_messages(read_messages(directory), load_labels(labels_path), org_domains)


def _summarize(rows: list[EmailRow], version: str, digest: str, threshold: float) -> ValidationReport:
    labeled = [row for row in rows if row.actual in {"phishing", "genuine"}]
    confusion = Confusion()
    for row in labeled:
        if row.actual == "phishing" and row.predicted == "phishing":
            confusion.tp += 1
        elif row.actual == "genuine" and row.predicted == "phishing":
            confusion.fp += 1
        elif row.actual == "genuine" and row.predicted == "genuine":
            confusion.tn += 1
        else:
            confusion.fn += 1
    correct = confusion.tp + confusion.tn
    accuracy = _ratio(correct, len(labeled))
    precision = _ratio(confusion.tp, confusion.tp + confusion.fp)
    recall = _ratio(confusion.tp, confusion.tp + confusion.fn)
    f1 = None
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = 2 * precision * recall / (precision + recall)
    mistakes = [row for row in labeled if row.correct is False]
    return ValidationReport(
        total=len(rows),
        labeled=len(labeled),
        actual_phishing=sum(1 for row in labeled if row.actual == "phishing"),
        actual_genuine=sum(1 for row in labeled if row.actual == "genuine"),
        predicted_phishing=sum(1 for row in rows if row.predicted == "phishing"),
        predicted_genuine=sum(1 for row in rows if row.predicted == "genuine"),
        correct=correct if labeled else None,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1=f1,
        false_positive_rate=_ratio(confusion.fp, confusion.fp + confusion.tn),
        false_negative_rate=_ratio(confusion.fn, confusion.fn + confusion.tp),
        confusion=confusion,
        per_email=rows,
        misclassifications=mistakes,
        engine_version=version or "0.1.0",
        weights_hash=digest,
        threshold=threshold,
    )


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator
