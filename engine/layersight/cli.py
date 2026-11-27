"""Command line fallback for analysis, validation, similarity, and comparison."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from layersight.config.adapter import ConfigError, load_config
from layersight.config.schema import LayerConfig
from layersight.features.domains import similarity
from layersight.refs import protected_domains
from layersight.scoring.analyze import analyze_email
from layersight.simulation.compare import aggregate, compare_email, narrative
from layersight.simulation.recommend import build_recommendations
from layersight.validation.metrics import read_messages, validate_directory

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


@app.command()
def analyze(
    path: Path,
    out: Path | None = typer.Option(None, "--out"),
    org_domain: list[str] | None = typer.Option(None, "--org-domain"),
) -> None:
    """Analyze one file or every email in a directory."""
    messages = _messages(path)
    payload = []
    for filename, raw in messages:
        bundle = analyze_email(raw, org_domain)
        payload.append({"filename": filename, **bundle.model_dump()})
    text = json.dumps(payload if len(payload) != 1 else payload[0], indent=2)
    if out:
        out.write_text(text + "\n", encoding="utf-8")
    else:
        console.print_json(text)


def _org_domains(path: Path, explicit: list[str] | None) -> list[str] | None:
    if explicit:
        return explicit
    root = path.parent if path.is_dir() else path.parent
    candidate = root / "configs" / "untrained.yaml"
    if not candidate.is_file():
        return None
    import yaml

    data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
    domains = data.get("org_domains") if isinstance(data, dict) else None
    if not isinstance(domains, list):
        return None
    return [str(item).lower() for item in domains]


@app.command("validate")
def validate_cmd(
    path: Path = typer.Argument(..., help="Directory of email files"),
    labels: Path = typer.Option(..., "--labels", help="CSV with filename,label"),
    org_domain: list[str] | None = typer.Option(None, "--org-domain"),
) -> None:
    """Score a labeled set. Exits non-zero when accuracy is under 0.90."""
    report = validate_directory(path, labels, _org_domains(path, org_domain))
    table = Table(title="Validation")
    table.add_column("File")
    table.add_column("Actual")
    table.add_column("Predicted")
    table.add_column("Risk", justify="right")
    table.add_column("Correct")
    for row in report.per_email:
        table.add_row(
            row.filename,
            row.actual or "—",
            row.predicted,
            f"{row.risk_score:.2f}",
            "—" if row.correct is None else ("yes" if row.correct else "no"),
        )
    console.print(table)
    if report.accuracy is None:
        console.print("No labels matched these files.")
        raise typer.Exit(code=1)
    console.print(
        f"{report.correct}/{report.labeled} correct, accuracy {report.accuracy:.1%}, "
        f"weights {report.weights_hash}"
    )
    for row in report.misclassifications:
        console.print(row.explanation or row.filename)
    if report.accuracy < 0.90:
        raise typer.Exit(code=1)


@app.command("similarity")
def similarity_cmd(
    domain: str = typer.Argument(..., metavar="DOMAIN"),
    org_domain: list[str] | None = typer.Option(None, "--org-domain"),
) -> None:
    """Score one domain against protected brands and organization domains."""
    result = similarity(domain, protected_domains(org_domain or ["company.com"]))
    console.print_json(json.dumps({
        "domain": domain,
        "score": result.score,
        "closest": result.closest,
        "technique": result.technique,
        "diff": [item.model_dump() for item in result.diff],
    }))


@app.command()
def simulate(
    path: Path,
    config: Path = typer.Option(..., "--config"),
    runs: int = typer.Option(10000, "--runs"),
    seed: int = typer.Option(42, "--seed"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Per-email and aggregate pass-through for predicted phishing."""
    layer_config, warnings = _load(config)
    rows = []
    skipped = 0
    for filename, raw in _messages(path):
        bundle = analyze_email(raw, layer_config.org_domains)
        if bundle.analysis.label != "phishing":
            skipped += 1
            continue
        from layersight.simulation.compare import simulate as run_sim

        result = run_sim(bundle.analysis, bundle.sha256, layer_config, runs=runs, seed=seed)
        low, high = result.ci95
        rows.append(
            {
                "filename": filename,
                "vector": result.attack_vector,
                "pass_rate": result.pass_rate,
                "closed_form": result.closed_form,
                "ci95": [low, high],
            }
        )
    if not rows:
        console.print("No phishing emails to simulate.")
        raise typer.Exit(code=1)
    payload = {
        "config": layer_config.name,
        "seed": seed,
        "runs": runs,
        "skipped_genuine": skipped,
        "emails": rows,
        "aggregate_closed_form": sum(row["closed_form"] for row in rows) / len(rows),
        "aggregate_pass_rate": sum(row["pass_rate"] for row in rows) / len(rows),
    }
    if as_json:
        console.print_json(json.dumps(payload))
        return
    for warning in warnings:
        console.print(f"warning: {warning}")
    table = Table(title=f"{layer_config.name}  ·  {runs:,} runs  ·  seed {seed}")
    table.add_column("Email")
    table.add_column("Vector")
    table.add_column("Closed form", justify="right")
    table.add_column("Monte Carlo", justify="right")
    table.add_column("95% CI", justify="right")
    for row in rows:
        low, high = row["ci95"]
        table.add_row(
            str(row["filename"]),
            str(row["vector"]).replace("_", " "),
            f"{float(row['closed_form']) * 100:.2f}%",
            f"{float(row['pass_rate']) * 100:.2f}%",
            f"{float(low) * 100:.2f}%–{float(high) * 100:.2f}%",
        )
    console.print(table)
    console.print(
        f"Aggregate pass-through (equal-weighted, {len(rows)} phishing"
        + (f", skipped {skipped} genuine" if skipped else "")
        + f"): closed form {float(payload['aggregate_closed_form']) * 100:.2f}%, "
        f"Monte Carlo {float(payload['aggregate_pass_rate']) * 100:.2f}%."
    )
    console.print(
        "Pass-through is a modeled estimate. "
        "Layers are assumed independent given the email."
    )


@app.command()
def compare(
    path: Path,
    config_a: Path = typer.Option(..., "--a"),
    config_b: Path = typer.Option(..., "--b"),
    runs: int = typer.Option(10000, "--runs"),
    seed: int = typer.Option(42, "--seed"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Compare two configs with the same random draws for each email."""
    left, warnings_a = _load(config_a)
    right, warnings_b = _load(config_b)
    per_email = []
    skipped = 0
    for filename, raw in _messages(path):
        bundle = analyze_email(raw, left.org_domains)
        if bundle.analysis.label != "phishing":
            skipped += 1
            continue
        item = compare_email(bundle.analysis, bundle.sha256, left, right, runs=runs, seed=seed)
        per_email.append((filename, item))
    if not per_email:
        console.print("No phishing emails to compare.")
        raise typer.Exit(code=1)
    lefts = [item.baseline.simulation for _, item in per_email]
    rights = [item.comparison.simulation for _, item in per_email]
    summary_left = aggregate(lefts)
    summary_right = aggregate(rights)
    sentence = narrative(left, right, summary_left.closed_form, summary_right.closed_form)
    if as_json:
        console.print_json(json.dumps({
            "narrative": sentence,
            "closed_form_a": summary_left.closed_form,
            "closed_form_b": summary_right.closed_form,
            "relative_reduction": _relative(summary_left.closed_form, summary_right.closed_form),
            "emails": [
                {
                    "filename": filename,
                    "closed_form_a": item.baseline.simulation.closed_form,
                    "closed_form_b": item.comparison.simulation.closed_form,
                }
                for filename, item in per_email
            ],
        }))
        return
    for warning in [*warnings_a, *warnings_b]:
        console.print(f"warning: {warning}")
    table = Table(title="Comparison")
    table.add_column("Email")
    table.add_column("A closed form", justify="right")
    table.add_column("B closed form", justify="right")
    table.add_column("A Monte Carlo", justify="right")
    table.add_column("B Monte Carlo", justify="right")
    for filename, item in per_email:
        table.add_row(
            filename,
            f"{item.baseline.simulation.closed_form * 100:.2f}%",
            f"{item.comparison.simulation.closed_form * 100:.2f}%",
            f"{item.baseline.simulation.pass_rate * 100:.2f}%",
            f"{item.comparison.simulation.pass_rate * 100:.2f}%",
        )
    console.print(table)
    console.print(
        f"A  {left.name}  closed form {summary_left.closed_form * 100:.2f}%  "
        f"Monte Carlo {summary_left.pass_rate * 100:.2f}%"
    )
    console.print(
        f"B  {right.name}  closed form {summary_right.closed_form * 100:.2f}%  "
        f"Monte Carlo {summary_right.pass_rate * 100:.2f}%"
    )
    if summary_left.closed_form > 0:
        reduction = _relative(summary_left.closed_form, summary_right.closed_form)
        console.print(f"Relative reduction {reduction * 100:.1f}%")
    if skipped:
        console.print(f"Skipped {skipped} genuine emails.")
    console.print(sentence)


@app.command()
def recommend(
    path: Path,
    config: Path = typer.Option(..., "--config"),
) -> None:
    """Rank the next control changes for the predicted phishing in a directory."""
    layer_config, warnings = _load(config)
    for warning in warnings:
        console.print(f"warning: {warning}")
    emails = []
    for _filename, raw in _messages(path):
        emails.append(analyze_email(raw, layer_config.org_domains).analysis)
    try:
        report = build_recommendations(emails, layer_config)
    except ValueError as exc:
        console.print(str(exc))
        raise typer.Exit(code=1) from exc
    console.print(f"Baseline modeled pass-through {report.baseline_pass_rate * 100:.2f}%")
    if not report.recommendations:
        console.print("No ranked intervention lowers pass-through for this set.")
    for index, item in enumerate(report.recommendations, start=1):
        console.print(f"{index}. {item.title}")
        console.print(f"   {item.detail}")
    table = Table(title="Sensitivity, each applicable layer ±10 points")
    table.add_column("Layer")
    table.add_column("Weaker", justify="right")
    table.add_column("Stronger", justify="right")
    table.add_column("Swing", justify="right")
    for bar in report.sensitivity:
        table.add_row(
            bar.layer,
            f"{bar.pass_rate_weaker * 100:.2f}%",
            f"{bar.pass_rate_stronger * 100:.2f}%",
            f"{bar.swing * 100:.2f}%",
        )
    console.print(table)


def _relative(before: float, after: float) -> float:
    if before <= 0:
        return 0.0
    return (before - after) / before


def _load(path: Path) -> tuple[LayerConfig, list[str]]:
    try:
        return load_config(path)
    except ConfigError as exc:
        console.print(exc.detail)
        raise typer.Exit(code=1) from exc


def _messages(path: Path) -> list[tuple[str, str]]:
    if path.is_dir():
        return read_messages(path)
    return [(path.name, path.read_text(encoding="utf-8", errors="replace"))]
