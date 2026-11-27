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

from app.db import Analysis, ConfigRow, Dataset, Email, RunRow, ensure_db
from layersight.config.adapter import load_config
from layersight.config.schema import LayerConfig
from layersight.scoring.analyze import analyze_email
from layersight.simulation.compare import compare_dataset, compare_email
from layersight.validation.metrics import validate_messages

MAX_FILES = 200
MAX_FILE = 2 * 1024 * 1024
MAX_REQUEST = 20 * 1024 * 1024


class APIError(Exception):
    def __init__(
        self, status: int, title: str, detail: str, fields: list[dict[str, str]] | None = None
    ) -> None:
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
        config_id = (
            "untrained"
            if "untrained" in path.name
            else "trained"
            if "trained" in path.name
            else path.stem
        )
        if db.get(ConfigRow, config_id) is not None:
            continue
        config, _warnings = load_config(path)
        db.add(ConfigRow(id=config_id, name=config.name, body=config.model_dump_json()))
    db.commit()


def list_configs(db: Session) -> list[dict[str, Any]]:
    seed_configs(db)
    rows = db.scalars(select(ConfigRow).order_by(ConfigRow.name)).all()
    return [{"id": row.id, "name": row.name} for row in rows]


def parse_config(payload: dict[str, Any]) -> LayerConfig:
    from pydantic import ValidationError

    try:
        return LayerConfig.model_validate(payload)
    except ValidationError as exc:
        fields = [
            {"field": ".".join(str(part) for part in error["loc"]), "message": error["msg"]}
            for error in exc.errors()
        ]
        raise APIError(
            422,
            "Invalid layer configuration",
            "The configuration does not match the schema.",
            fields,
        ) from exc


def get_config(db: Session, config_id: str) -> dict[str, Any]:
    seed_configs(db)
    row = db.get(ConfigRow, config_id)
    if row is None:
        raise APIError(404, "No configuration", "That configuration is not stored.")
    config = LayerConfig.model_validate_json(row.body)
    return {"id": row.id, "name": row.name, "config": config.model_dump(mode="json")}


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


def _pair(
    db: Session, baseline_id: str | None, comparison_id: str | None
) -> tuple[LayerConfig, LayerConfig]:
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
        raise APIError(
            400,
            "Nothing stored",
            "Every file was empty, too large, or a duplicate.",
            [{"field": "files", "message": "; ".join(warnings)}],
        )
    db.commit()
    return {"id": dataset.id, "name": dataset.name, "emails": stored, "warnings": warnings}


def reset_demo(db: Session) -> dict[str, Any]:
    for dataset in db.scalars(select(Dataset)).all():
        email_ids = list(db.scalars(select(Email.id).where(Email.dataset_id == dataset.id)))
        if email_ids:
            db.query(Analysis).filter(Analysis.email_id.in_(email_ids)).delete(
                synchronize_session=False
            )
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
        select(Email, Analysis)
        .join(Analysis, Analysis.email_id == Email.id)
        .where(Email.dataset_id == dataset_id)
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
    labels = {
        email.filename: email.ground_truth for email, _analysis in joined if email.ground_truth
    }
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
    writer.writerow(
        [
            "filename",
            "subject",
            "ground_truth",
            "prediction",
            "risk_score",
            "band",
            "attack_vector",
            "correct",
            "top_evidence",
        ]
    )
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
            raise APIError(
                400, "Unsafe zip", f"{filename} contains a path that leaves the archive."
            )
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


def import_config_text(db: Session, filename: str, text: str) -> dict[str, Any]:
    import yaml

    from layersight.config.adapter import ConfigError, adapt

    loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        raise APIError(422, "Invalid layer configuration", "The file must be a YAML mapping.")
    try:
        config, warnings = adapt(loaded, source=filename or "upload")
    except ConfigError as exc:
        raise APIError(422, "Invalid layer configuration", exc.detail, exc.fields) from exc
    row_id = Path(filename).stem or str(uuid.uuid4())
    payload = config.model_dump_json()
    existing = db.get(ConfigRow, row_id)
    if existing is None:
        db.add(ConfigRow(id=row_id, name=config.name, body=payload))
    else:
        existing.name = config.name
        existing.body = payload
    db.commit()
    return {
        "id": row_id,
        "name": config.name,
        "warnings": warnings,
        "config": config.model_dump(mode="json"),
    }


def simulate_dataset(
    db: Session,
    dataset_id: str,
    config_id: str | None,
    *,
    runs: int = 10000,
    seed: int = 42,
    persist: bool = True,
    config: LayerConfig | None = None,
    closed_form_only: bool = False,
) -> dict[str, Any]:
    from layersight.models import Bundle
    from layersight.simulation.compare import simulate

    chosen = config if config is not None else _config(db, config_id, "untrained")
    per_email: list[dict[str, Any]] = []
    for email, analysis_row in _joined(db, dataset_id):
        bundle = Bundle.model_validate_json(analysis_row.payload)
        if bundle.analysis.label != "phishing":
            continue
        if closed_form_only:
            item = _closed_form_email(bundle.analysis, chosen, runs)
        else:
            simulated = simulate(bundle.analysis, email.sha256, chosen, runs=runs, seed=seed)
            item = simulated.model_dump(mode="json")
        item["filename"] = email.filename
        item["id"] = email.id
        item["subject"] = bundle.presentation.subject
        per_email.append(item)
    body = _simulation_body(
        dataset_id,
        chosen,
        config_id or ("inline" if config is not None else "untrained"),
        per_email,
        runs,
        seed,
    )
    if not persist:
        body["id"] = None
        return body
    run_id = str(uuid.uuid4())
    body["id"] = run_id
    db.add(
        RunRow(
            id=run_id,
            dataset_id=dataset_id,
            kind="simulation",
            runs=runs,
            seed=seed,
            body=json.dumps(body),
        )
    )
    db.commit()
    return body


def load_run(db: Session, run_id: str) -> dict[str, Any]:
    row = db.get(RunRow, run_id)
    if row is None:
        raise APIError(404, "Run not found", "That simulation is not in this database.")
    loaded = json.loads(row.body)
    if not isinstance(loaded, dict):
        raise APIError(500, "Stored run is unreadable", "The saved simulation is not valid JSON.")
    return loaded


def compare_configs(
    db: Session,
    dataset_id: str,
    config_a_id: str | None,
    config_b_id: str | None,
    *,
    runs: int = 10000,
    seed: int = 42,
    config_a: LayerConfig | None = None,
    config_b: LayerConfig | None = None,
) -> dict[str, Any]:
    from layersight import __version__
    from layersight.models import Bundle
    from layersight.simulation.compare import compare_email, narrative

    left = config_a if config_a is not None else _config(db, config_a_id, "untrained")
    right = config_b if config_b is not None else _config(db, config_b_id, "trained")
    deltas: list[dict[str, Any]] = []
    per_a: list[dict[str, Any]] = []
    per_b: list[dict[str, Any]] = []
    for email, analysis_row in _joined(db, dataset_id):
        bundle = Bundle.model_validate_json(analysis_row.payload)
        if bundle.analysis.label != "phishing":
            continue
        item = compare_email(bundle.analysis, email.sha256, left, right, runs=runs, seed=seed)
        left_item = item.baseline.simulation.model_dump(mode="json")
        right_item = item.comparison.simulation.model_dump(mode="json")
        for side in (left_item, right_item):
            side["filename"] = email.filename
            side["id"] = email.id
            side["subject"] = bundle.presentation.subject
        per_a.append(left_item)
        per_b.append(right_item)
        deltas.append(
            {
                "email_id": email.id,
                "filename": email.filename,
                "subject": bundle.presentation.subject,
                "sha256": email.sha256,
                "attack_vector": bundle.analysis.attack_vector,
                "pass_rate_a": item.baseline.simulation.pass_rate,
                "pass_rate_b": item.comparison.simulation.pass_rate,
                "closed_form_a": item.baseline.simulation.closed_form,
                "closed_form_b": item.comparison.simulation.closed_form,
                "absolute_reduction": item.baseline.simulation.closed_form
                - item.comparison.simulation.closed_form,
            }
        )
    before = _mean_closed(per_a)
    after = _mean_closed(per_b)
    relative = 0.0 if before <= 0 else (before - after) / before
    body = {
        "dataset_id": dataset_id,
        "config_a_id": config_a_id or "inline",
        "config_b_id": config_b_id or "inline",
        "config_a_name": left.name,
        "config_b_name": right.name,
        "runs": runs,
        "seed": seed,
        "engine_version": __version__,
        "absolute_reduction": before - after,
        "relative_reduction": relative,
        "narrative": narrative(left, right, before, after),
        "changes": config_changes(left, right),
        "per_email": deltas,
        "result_a": _simulation_body(dataset_id, left, config_a_id or "inline", per_a, runs, seed),
        "result_b": _simulation_body(dataset_id, right, config_b_id or "inline", per_b, runs, seed),
    }
    run_id = str(uuid.uuid4())
    body["id"] = run_id
    db.add(
        RunRow(
            id=run_id,
            dataset_id=dataset_id,
            kind="comparison",
            runs=runs,
            seed=seed,
            body=json.dumps(body),
        )
    )
    db.commit()
    return body


def recommend_dataset(
    db: Session,
    dataset_id: str,
    config_id: str | None,
    config: LayerConfig | None = None,
) -> dict[str, Any]:
    from layersight.models import Bundle
    from layersight.refs import assumptions
    from layersight.simulation.model import layer_probabilities
    from layersight.simulation.montecarlo import closed_form

    config = config if config is not None else _config(db, config_id, "untrained")
    analyses = []
    for _email, analysis_row in _joined(db, dataset_id):
        bundle = Bundle.model_validate_json(analysis_row.payload)
        if bundle.analysis.label == "phishing":
            analyses.append(bundle.analysis)
    if not analyses:
        return {"base_pass_rate": 0.0, "recommendations": [], "sensitivity": []}
    table = assumptions()

    def mean_closed(current: LayerConfig) -> float:
        rates = [
            closed_form([layer.p_stop for layer in layer_probabilities(item, current, table)])
            for item in analyses
        ]
        return sum(rates) / len(rates)

    base = mean_closed(config)
    recommendations: list[dict[str, Any]] = []
    for candidate_id, title, detail, layer, updated in _recommendation_candidates(config):
        rate = mean_closed(updated)
        reduction = base - rate
        if reduction <= 1e-6:
            continue
        helped = {
            item.attack_vector
            for item in analyses
            if closed_form([layer.p_stop for layer in layer_probabilities(item, config, table)])
            - closed_form([layer.p_stop for layer in layer_probabilities(item, updated, table)])
            > 1e-6
        }
        recommendations.append(
            {
                "id": candidate_id,
                "title": title,
                "detail": detail,
                "layer": layer,
                "absolute_reduction": reduction,
                "relative_reduction": 0.0 if base <= 0 else reduction / base,
                "vectors_helped": sorted(helped),
            }
        )
    recommendations.sort(key=lambda item: (-float(item["absolute_reduction"]), str(item["title"])))
    names = ("email_filter", "user", "application_control", "antivirus", "segmentation")
    sensitivity = []
    for index, name in enumerate(names):
        sensitivity.append(
            {
                "layer": name,
                "baseline": base,
                "decreased": _shifted(analyses, config, table, index, -0.1),
                "increased": _shifted(analyses, config, table, index, 0.1),
            }
        )
    return {"base_pass_rate": base, "recommendations": recommendations, "sensitivity": sensitivity}


def override_vector(db: Session, email_id: str, attack_vector: str) -> dict[str, Any]:
    email = db.get(Email, email_id)
    if email is None:
        raise APIError(404, "Email not found", "That email is not in this database.")
    analysis_row = db.scalar(select(Analysis).where(Analysis.email_id == email_id))
    if analysis_row is None:
        raise APIError(404, "Analysis missing", "This email has no stored analysis.")
    payload = json.loads(analysis_row.payload)
    payload["analysis"]["attack_vector"] = attack_vector
    payload["analysis"]["vector_reason"] = "An analyst overrode the attack vector."
    analysis_row.payload = json.dumps(payload)
    analysis_row.label = payload["analysis"]["label"]
    db.commit()
    return email_detail(db, email_id, baseline_id=None, comparison_id=None, runs=1000, seed=42)


def _mean_closed(per_email: list[dict[str, Any]]) -> float:
    if not per_email:
        return 0.0
    return sum(float(item["closed_form"]) for item in per_email) / len(per_email)


def _simulation_body(
    dataset_id: str,
    config: LayerConfig,
    config_id: str,
    per_email: list[dict[str, Any]],
    runs: int,
    seed: int,
) -> dict[str, Any]:
    from layersight import __version__
    from layersight.simulation.montecarlo import wilson

    closed = _mean_closed(per_email)
    rate = (
        sum(float(item["pass_rate"]) for item in per_email) / len(per_email) if per_email else 0.0
    )
    passed = sum(int(item["passed"]) for item in per_email)
    low, high = wilson(passed, max(len(per_email), 1) * runs)
    return {
        "dataset_id": dataset_id,
        "config_id": config_id,
        "runs": runs,
        "seed": seed,
        "engine_version": __version__,
        "config_snapshot": config.model_dump(mode="json"),
        "per_email": per_email,
        "aggregate": {
            "email_count": len(per_email),
            "runs": runs,
            "pass_rate": rate,
            "blocked_rate": 1.0 - rate,
            "closed_form": closed,
            "ci95": [low, high],
            "layers": _mean_layers(per_email),
        },
    }


def _closed_form_email(analysis: Any, config: LayerConfig, runs: int) -> dict[str, Any]:
    from layersight.refs import assumptions
    from layersight.simulation.model import layer_probabilities
    from layersight.simulation.montecarlo import closed_form

    layers = layer_probabilities(analysis, config, assumptions())
    form = closed_form([layer.p_stop for layer in layers])
    entered = runs
    filled: list[dict[str, Any]] = []
    for layer in layers:
        dumped = layer.model_dump(mode="json")
        if not layer.applicable:
            dumped["entered"] = 0
            dumped["stopped"] = 0
            filled.append(dumped)
            continue
        stopped = int(round(entered * layer.p_stop))
        dumped["entered"] = entered
        dumped["stopped"] = stopped
        filled.append(dumped)
        entered -= stopped
    return {
        "email_id": analysis.email_id,
        "attack_vector": analysis.attack_vector,
        "layers": filled,
        "passed": entered,
        "pass_rate": form,
        "ci95": [form, form],
        "closed_form": form,
    }


def _scalar(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return None


def config_changes(before: LayerConfig, after: LayerConfig) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []

    def push(path: str, left: Any, right: Any) -> None:
        if left == right:
            return
        if isinstance(left, float) and isinstance(right, float) and abs(left - right) < 1e-9:
            return
        changes.append({"path": path, "before": _scalar(left), "after": _scalar(right)})

    push("name", before.name, after.name)
    push("org_domains", ",".join(before.org_domains), ",".join(after.org_domains))
    push(
        "email_filter.base_catch_rate",
        before.email_filter.base_catch_rate,
        after.email_filter.base_catch_rate,
    )
    push("user_training.level", before.user_training.level, after.user_training.level)
    push(
        "user_training.catch_rate",
        before.user_training.catch_rate,
        after.user_training.catch_rate,
    )
    push(
        "application_control.effectiveness",
        before.application_control.effectiveness,
        after.application_control.effectiveness,
    )
    keys = set(before.application_control.overrides) | set(after.application_control.overrides)
    for key in sorted(keys):
        push(
            f"application_control.overrides.{key}",
            before.application_control.overrides.get(key),
            after.application_control.overrides.get(key),
        )
    push(
        "antivirus.detection_rate", before.antivirus.detection_rate, after.antivirus.detection_rate
    )
    push(
        "segmentation.containment_rate",
        before.segmentation.containment_rate,
        after.segmentation.containment_rate,
    )
    push(
        "segmentation.applies_to_credential_harvest",
        before.segmentation.applies_to_credential_harvest,
        after.segmentation.applies_to_credential_harvest,
    )
    before_rules = {rule.id: rule for rule in before.email_filter.rules}
    after_rules = {rule.id: rule for rule in after.email_filter.rules}
    for rule_id in sorted(set(before_rules) | set(after_rules)):
        left = before_rules.get(rule_id)
        right = after_rules.get(rule_id)
        if left is None or right is None:
            changes.append(
                {
                    "path": f"email_filter.rules.{rule_id}",
                    "before": "present" if left else None,
                    "after": "present" if right else None,
                }
            )
            continue
        push(f"email_filter.rules.{rule_id}.enabled", left.enabled, right.enabled)
        push(f"email_filter.rules.{rule_id}.catch_rate", left.catch_rate, right.catch_rate)
    return changes


def _mean_layers(per_email: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not per_email or not per_email[0].get("layers"):
        return []
    count = len(per_email)
    rows: list[dict[str, Any]] = []
    for index, layer in enumerate(per_email[0]["layers"]):
        rows.append(
            {
                "layer": layer["layer"],
                "applicable": any(item["layers"][index]["applicable"] for item in per_email),
                "p_stop": sum(float(item["layers"][index]["p_stop"]) for item in per_email) / count,
                "reasons": ["Equal-weighted mean across predicted phishing emails."],
                "entered": int(
                    round(sum(int(item["layers"][index]["entered"]) for item in per_email) / count)
                ),
                "stopped": int(
                    round(sum(int(item["layers"][index]["stopped"]) for item in per_email) / count)
                ),
            }
        )
    return rows


def _shifted(
    analyses: list[Any],
    config: LayerConfig,
    table: Any,
    index: int,
    delta: float,
) -> float:
    from layersight.simulation.model import layer_probabilities
    from layersight.simulation.montecarlo import closed_form

    rates: list[float] = []
    for analysis in analyses:
        layers = layer_probabilities(analysis, config, table)
        probabilities: list[float] = []
        for position, layer in enumerate(layers):
            probability = layer.p_stop
            if position == index and layer.applicable:
                probability = min(0.98, max(0.0, probability + delta))
            probabilities.append(probability)
        rates.append(closed_form(probabilities))
    return sum(rates) / len(rates) if rates else 0.0


def _recommendation_candidates(config: LayerConfig) -> list[tuple[str, str, str, str, LayerConfig]]:
    from layersight.config.schema import FilterRule, Match

    found: list[tuple[str, str, str, str, LayerConfig]] = []
    levels = ["none", "basic", "advanced"]
    level = config.user_training.level
    if config.user_training.catch_rate is None and level in levels[:-1]:
        nxt = levels[levels.index(level) + 1]
        found.append(
            (
                "raise_training",
                f"Advance user training to {nxt}",
                "Training changes every phishing email, including ones antivirus cannot see.",
                "user",
                config.model_copy(
                    update={"user_training": config.user_training.model_copy(update={"level": nxt})}
                ),
            )
        )
    if not any(
        rule.id == "quarantine_dmarc_fail" and rule.enabled for rule in config.email_filter.rules
    ):
        rule = FilterRule(
            id="quarantine_dmarc_fail",
            description="Quarantine messages that fail DMARC",
            match=Match(feature="auth.dmarc", op="eq", value="fail"),
            catch_rate=0.85,
        )
        rules = [*config.email_filter.rules, rule]
        found.append(
            (
                "quarantine_dmarc",
                "Quarantine DMARC failures",
                "Add a filter rule that catches DMARC failures at 85%.",
                "email_filter",
                config.model_copy(
                    update={"email_filter": config.email_filter.model_copy(update={"rules": rules})}
                ),
            )
        )
    if config.antivirus.detection_rate < 0.99:
        found.append(
            (
                "antivirus_detection",
                "Raise antivirus detection 15 points",
                "Endpoint detection only changes malware.",
                "antivirus",
                config.model_copy(
                    update={
                        "antivirus": config.antivirus.model_copy(
                            update={
                                "detection_rate": min(
                                    1.0, round(config.antivirus.detection_rate + 0.15, 3)
                                )
                            }
                        )
                    }
                ),
            )
        )
    return found
