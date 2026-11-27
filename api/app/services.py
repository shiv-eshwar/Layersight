"""Ingest, list, investigate, and validate. Numbers come from the engine."""

from __future__ import annotations

import csv
import io
import json
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from layersight.config.adapter import load_config
from layersight.config.schema import LayerConfig
from layersight.scoring.analyze import analyze_email
from layersight.simulation.compare import compare_dataset, compare_email
from layersight.validation.metrics import validate_messages

from app.db import Analysis, ConfigRow, Dataset, Email, ensure_db

MAX_FILES = 200
MAX_FILE = 2 * 1024 * 1024
MAX_REQUEST = 20 * 1024 * 1024


class APIError(Exception):
    def __init__(self, status: int, title: str, detail: str, fields: list[dict[str, str]] | None = None) -> None:
        super().__init__(detail)
        self.status = status
        self.title = title
        self.detail = detail
        self.fields = fields or []


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "data").is_dir() and (parent / "engine").is_dir():
            return parent
    raise APIError(500, "Data directory missing", "The API cannot find the data directory.")


def seed_configs(db: Session) -> None:
    root = repo_root()
    folder = root / "data" / "test" / "configs"
    if not any(folder.glob("*.yaml")):
        folder = root / "data" / "dev" / "configs"
    for path in sorted(folder.glob("*.yaml")):
        config_id = "untrained" if "untrained" in path.name else "trained" if "trained" in path.name else path.stem
        if db.get(ConfigRow, config_id) is not None:
            continue
        config, _warnings = load_config(path)
        db.add(ConfigRow(id=config_id, name=config.name, body=config.model_dump_json()))
    db.commit()


def list_configs(db: Session) -> list[dict[str, Any]]:
    seed_configs(db)
    rows = db.scalars(select(ConfigRow).order_by(ConfigRow.name)).all()
    return [{"id": row.id, "name": row.name} for row in rows]


def _config(db: Session, config_id: str | None, fallback: str) -> LayerConfig:
    seed_configs(db)
    row = db.get(ConfigRow, config_id) if config_id else None
    if row is None:
        row = db.get(ConfigRow, fallback)
    if row is None:
        rows = db.scalars(select(ConfigRow)).all()
        row = rows[0] if rows else None
    if row is None:
        raise APIError(404, "No configuration", "Import a layer configuration before simulating.")
    return LayerConfig.model_validate_json(row.body)


def _pair(db: Session, baseline_id: str | None, comparison_id: str | None) -> tuple[LayerConfig, LayerConfig]:
    return _config(db, baseline_id, "untrained"), _config(db, comparison_id, "trained")


def ingest(
    db: Session,
    files: list[tuple[str, bytes]],
    labels_csv: str | None,
    name: str | None,
    source: str = "upload",
) -> dict[str, Any]:
    if not files:
        raise APIError(400, "No files", "Choose at least one .eml, .txt, or .zip file.")
    expanded, warnings = _expand(files)
    if len(expanded) > MAX_FILES:
        raise APIError(400, "Too many files", f"A dataset can hold {MAX_FILES} emails.")
    labels = _labels(labels_csv) if labels_csv else {}
    dataset = Dataset(
        id=str(uuid.uuid4()),
        name=name or "Upload",
        source=source,
        created_at=datetime.now(UTC),
    )
    db.add(dataset)
    seen: set[str] = set()
    stored = 0
    org = _config(db, "untrained", "untrained").org_domains
    for filename, raw_bytes in expanded:
        if len(raw_bytes) > MAX_FILE:
            warnings.append(f"{filename} is larger than 2 MB and was skipped.")
            continue
        text = raw_bytes.decode("utf-8", errors="replace")
        bundle = analyze_email(text, org)
        if bundle.sha256 in seen:
            warnings.append(f"{filename} duplicates another file in this upload and was skipped.")
            continue
        seen.add(bundle.sha256)
        email = Email(
            id=str(uuid.uuid4()),
            dataset_id=dataset.id,
            filename=Path(filename).name,
            sha256=bundle.sha256,
            raw_text=text,
            ground_truth=labels.get(Path(filename).name),
        )
        db.add(email)
        db.add(
            Analysis(
                id=str(uuid.uuid4()),
                email_id=email.id,
                engine_version=bundle.analysis.engine_version,
                weights_hash=bundle.analysis.weights_hash,
                risk_score=bundle.analysis.risk_score,
                label=bundle.analysis.label,
                payload=bundle.model_dump_json(),
            )
        )
        stored += 1
    if stored == 0:
        raise APIError(400, "Nothing stored", "Every file was empty, too large, or a duplicate.", [{"field": "files", "message": "; ".join(warnings)}])
    db.commit()
    return {"id": dataset.id, "name": dataset.name, "emails": stored, "warnings": warnings}


def reset_demo(db: Session) -> dict[str, Any]:
    for dataset in db.scalars(select(Dataset)).all():
        email_ids = list(db.scalars(select(Email.id).where(Email.dataset_id == dataset.id)))
        if email_ids:
            db.query(Analysis).filter(Analysis.email_id.in_(email_ids)).delete(synchronize_session=False)
        db.query(Email).filter(Email.dataset_id == dataset.id).delete(synchronize_session=False)
        db.delete(dataset)
    db.commit()
    root = repo_root() / "data" / "test"
    emails = sorted((root / "emails").glob("*.eml"))
    if not emails:
        raise APIError(404, "Test set missing", "data/test/emails has no messages to load.")
    label_path = root / "labels.csv"
    files = [(path.name, path.read_bytes()) for path in emails]
    labels = label_path.read_text(encoding="utf-8") if label_path.is_file() else None
    created = ingest(db, files, labels, "Practice test set", source="test")
    return created


def list_datasets(db: Session) -> list[dict[str, Any]]:
    rows = db.scalars(select(Dataset).order_by(Dataset.created_at.desc())).all()
    result = []
    for row in rows:
        count = len(db.scalars(select(Email.id).where(Email.dataset_id == row.id)).all())
        result.append(
            {
                "id": row.id,
                "name": row.name,
                "source": row.source,
                "emails": count,
                "created_at": row.created_at.isoformat(),
            }
        )
    return result


def _joined(db: Session, dataset_id: str) -> list[tuple[Email, Analysis]]:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise APIError(404, "Dataset not found", "That dataset is not in this database.")
    rows = db.execute(
        select(Email, Analysis).join(Analysis, Analysis.email_id == Email.id).where(Email.dataset_id == dataset_id)
    ).all()
    return [(email, analysis) for email, analysis in rows]


def list_emails(
    db: Session,
    dataset_id: str,
    *,
    q: str = "",
    prediction: str = "all",
    sort: str = "-risk",
) -> dict[str, Any]:
    joined = _joined(db, dataset_id)
    records = [_row(email, analysis) for email, analysis in joined]
    counts = {
        "all": len(records),
        "phishing": sum(1 for row in records if row["prediction"] == "phishing"),
        "genuine": sum(1 for row in records if row["prediction"] == "genuine"),
    }
    needle = q.strip().lower()
    filtered = records
    if prediction in {"phishing", "genuine"}:
        filtered = [row for row in filtered if row["prediction"] == prediction]
    if needle:
        filtered = [
            row
            for row in filtered
            if needle in row["subject"].lower()
            or needle in row["sender"].lower()
            or needle in row["sender_domain"].lower()
        ]
    reverse = sort.startswith("-")
    key = sort.lstrip("-")
    if key == "subject":
        filtered.sort(key=lambda row: row["subject"].lower(), reverse=reverse)
    elif key == "sender":
        filtered.sort(key=lambda row: row["sender"].lower(), reverse=reverse)
    elif key == "date":
        filtered.sort(key=lambda row: row["date"] or "", reverse=reverse)
    else:
        filtered.sort(key=lambda row: float(row["risk_score"]), reverse=sort != "risk")
    return {"dataset_id": dataset_id, "counts": counts, "emails": filtered}


def email_detail(
    db: Session,
    email_id: str,
    *,
    baseline_id: str | None,
    comparison_id: str | None,
    runs: int = 10000,
    seed: int = 42,
) -> dict[str, Any]:
    email = db.get(Email, email_id)
    if email is None:
        raise APIError(404, "Email not found", "That email is not in this database.")
    analysis_row = db.scalar(select(Analysis).where(Analysis.email_id == email_id))
    if analysis_row is None:
        raise APIError(404, "Analysis missing", "This email has no stored analysis.")
    payload = json.loads(analysis_row.payload)
    outlook = None
    if payload["analysis"]["label"] == "phishing":
        baseline, comparison = _pair(db, baseline_id, comparison_id)
        from layersight.models import EmailAnalysis

        analyzed = EmailAnalysis.model_validate(payload["analysis"])
        compared = compare_email(analyzed, email.sha256, baseline, comparison, runs=runs, seed=seed)
        outlook = compared.model_dump(mode="json")
    return {
        "id": email.id,
        "dataset_id": email.dataset_id,
        "filename": email.filename,
        "ground_truth": email.ground_truth,
        "sha256": email.sha256,
        "presentation": payload["presentation"],
        "analysis": payload["analysis"],
        "outlook": outlook,
    }


def validation_report(
    db: Session,
    dataset_id: str,
    *,
    baseline_id: str | None,
    comparison_id: str | None,
    runs: int = 10000,
    seed: int = 42,
) -> dict[str, Any]:
    joined = _joined(db, dataset_id)
    messages = [(email.filename, email.raw_text) for email, _analysis in joined]
    labels = {email.filename: email.ground_truth for email, _analysis in joined if email.ground_truth}
    org = _config(db, baseline_id, "untrained").org_domains
    report = validate_messages(messages, labels, org)
    body = report.model_dump(mode="json")
    pairs = []
    from layersight.models import Bundle

    for email, analysis_row in joined:
        bundle = Bundle.model_validate_json(analysis_row.payload)
        pairs.append((bundle.analysis, email.sha256))
    baseline, comparison = _pair(db, baseline_id, comparison_id)
    compared = compare_dataset(pairs, baseline, comparison, runs=runs, seed=seed)
    dataset = db.get(Dataset, dataset_id)
    body["dataset_name"] = dataset.name if dataset else ""
    body["dataset_source"] = dataset.source if dataset else ""
    body["pass_through"] = compared.model_dump(mode="json")
    body["notes"] = []
    if dataset is not None and dataset.source == "test":
        body["notes"].append(
            "This is the practice test set (12 phishing, 8 genuine), not an official file drop. Labels were not shown to the classifier."
        )
    return body


def report_csv(report: dict[str, Any]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["filename", "subject", "ground_truth", "prediction", "risk_score", "band", "attack_vector", "correct", "top_evidence"])
    for row in report["per_email"]:
        writer.writerow(
            [
                row["filename"],
                row["subject"],
                row.get("actual") or "",
                row["predicted"],
                f"{row['risk_score']:.4f}",
                row["band"],
                row["attack_vector"],
                "" if row["correct"] is None else ("yes" if row["correct"] else "no"),
                row.get("top_evidence") or "",
            ]
        )
    return buffer.getvalue()


def _row(email: Email, analysis: Analysis) -> dict[str, Any]:
    payload = json.loads(analysis.payload)
    presentation = payload["presentation"]
    analyzed = payload["analysis"]
    sender = presentation["sender"]
    display = sender.get("display_name") or ""
    address = sender.get("address") or ""
    sender_text = f"{display} <{address}>" if display else address
    top = next((item["title"] for item in analyzed["evidence"] if item["contribution"] > 0), None)
    return {
        "id": email.id,
        "filename": email.filename,
        "subject": presentation.get("subject") or "(no subject)",
        "sender": sender_text or "Unknown sender",
        "sender_domain": sender.get("registrable_domain") or "",
        "prediction": analyzed["label"],
        "band": analyzed["band"],
        "risk_score": analyzed["risk_score"],
        "attack_vector": analyzed["attack_vector"],
        "top_evidence": top,
        "date": presentation.get("date"),
        "ground_truth": email.ground_truth,
    }


def _labels(text: str) -> dict[str, str]:
    reader = csv.DictReader(io.StringIO(text))
    labels: dict[str, str] = {}
    for row in reader:
        filename = (row.get("filename") or row.get("file") or "").strip()
        label = (row.get("label") or "").strip().lower()
        if filename and label in {"phishing", "genuine"}:
            labels[Path(filename).name] = label
    return labels


def _expand(files: list[tuple[str, bytes]]) -> tuple[list[tuple[str, bytes]], list[str]]:
    expanded: list[tuple[str, bytes]] = []
    warnings: list[str] = []
    total = 0
    for filename, data in files:
        total += len(data)
        if total > MAX_REQUEST:
            raise APIError(400, "Upload too large", "The upload is larger than 20 MB.")
        if filename.lower().endswith(".zip"):
            expanded.extend(_zip(filename, data, warnings))
            continue
        suffix = Path(filename).suffix.lower()
        if suffix not in {".eml", ".txt"}:
            warnings.append(f"{filename} is not an .eml, .txt, or .zip file and was skipped.")
            continue
        expanded.append((Path(filename).name, data))
    return expanded, warnings


def _zip(filename: str, data: bytes, warnings: list[str]) -> list[tuple[str, bytes]]:
    found: list[tuple[str, bytes]] = []
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise APIError(400, "Bad zip", f"{filename} is not a zip file.") from exc
    for info in archive.infolist():
        if info.is_dir():
            continue
        parts = Path(info.filename).parts
        if info.filename.startswith("/") or ".." in parts:
            raise APIError(400, "Unsafe zip", f"{filename} contains a path that leaves the archive.")
        if info.file_size > MAX_FILE:
            warnings.append(f"{info.filename} is larger than 2 MB and was skipped.")
            continue
        name = Path(info.filename).name
        if Path(name).suffix.lower() not in {".eml", ".txt"}:
            continue
        found.append((name, archive.read(info)))
    if not found:
        warnings.append(f"{filename} did not contain any .eml or .txt files.")
    return found


def open_session() -> Session:
    return ensure_db()()
