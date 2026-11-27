"""Compare two configs with the same random draws."""

from __future__ import annotations

import numpy as np

from layersight import __version__
from layersight.config.schema import LayerConfig
from layersight.models import (
    EmailAnalysis,
    EmailComparison,
    EmailSimulation,
    LayerOutcome,
    SideResult,
)
from layersight.refs import Assumptions, assumptions
from layersight.simulation.model import layer_probabilities
from layersight.simulation.montecarlo import closed_form, run, uniforms, wilson


def aggregate(sims: list[EmailSimulation]) -> EmailSimulation:
    """Equal-weighted mean of per-email rates and funnels."""

    if not sims:
        return _empty("aggregate", "credential_harvest")
    return _mean(sims, "aggregate")


def simulate(
    analysis: EmailAnalysis,
    sha256: str,
    config: LayerConfig,
    *,
    runs: int | None = None,
    seed: int | None = None,
    table: Assumptions | None = None,
    draws: np.ndarray | None = None,
) -> EmailSimulation:
    table = table or assumptions()
    runs = runs if runs is not None else config.simulation.runs
    seed = seed if seed is not None else config.simulation.seed
    layers = layer_probabilities(analysis, config, table)
    p_stop = np.array([layer.p_stop for layer in layers], dtype=float)
    matrix = draws if draws is not None else uniforms(seed, sha256, runs)
    counts = run(p_stop, matrix)
    passed = int(counts[-1])
    entered = runs
    filled: list[LayerOutcome] = []
    for index, layer in enumerate(layers):
        stopped = int(counts[index])
        filled.append(layer.model_copy(update={"entered": int(entered), "stopped": stopped}))
        entered -= stopped
    form = closed_form([layer.p_stop for layer in layers])
    return EmailSimulation(
        email_id=analysis.email_id,
        attack_vector=analysis.attack_vector,
        layers=filled,
        passed=passed,
        pass_rate=passed / runs if runs else 0.0,
        ci95=wilson(passed, runs),
        closed_form=form,
    )


def compare_email(
    analysis: EmailAnalysis,
    sha256: str,
    baseline: LayerConfig,
    other: LayerConfig,
    *,
    runs: int = 10000,
    seed: int = 42,
) -> EmailComparison:
    draws = uniforms(seed, sha256, runs)
    left = simulate(analysis, sha256, baseline, runs=runs, seed=seed, draws=draws)
    right = simulate(analysis, sha256, other, runs=runs, seed=seed, draws=draws)
    return _pack(baseline, other, left, right, seed, runs)


def compare_dataset(
    rows: list[tuple[EmailAnalysis, str]],
    baseline: LayerConfig,
    other: LayerConfig,
    *,
    runs: int = 10000,
    seed: int = 42,
) -> EmailComparison:
    phishing = [(analysis, sha) for analysis, sha in rows if analysis.label == "phishing"]
    if not phishing:
        empty = _empty(baseline.name, "credential_harvest")
        return _pack(baseline, other, empty, _empty(other.name, "credential_harvest"), seed, runs)
    lefts: list[EmailSimulation] = []
    rights: list[EmailSimulation] = []
    for analysis, sha in phishing:
        draws = uniforms(seed, sha, runs)
        lefts.append(simulate(analysis, sha, baseline, runs=runs, seed=seed, draws=draws))
        rights.append(simulate(analysis, sha, other, runs=runs, seed=seed, draws=draws))
    return _pack(baseline, other, _mean(lefts, "aggregate"), _mean(rights, "aggregate"), seed, runs)


def _mean(sims: list[EmailSimulation], email_id: str) -> EmailSimulation:
    count = len(sims)
    layers: list[LayerOutcome] = []
    for index, layer in enumerate(sims[0].layers):
        layers.append(
            layer.model_copy(
                update={
                    "p_stop": sum(item.layers[index].p_stop for item in sims) / count,
                    "entered": int(round(sum(item.layers[index].entered for item in sims) / count)),
                    "stopped": int(round(sum(item.layers[index].stopped for item in sims) / count)),
                    "applicable": any(item.layers[index].applicable for item in sims),
                    "reasons": ["Equal-weighted mean across predicted phishing emails."],
                }
            )
        )
    passed = sum(item.passed for item in sims)
    runs = sims[0].layers[0].entered if sims[0].layers else 1
    total = passed
    pooled = count * runs
    form = sum(item.closed_form for item in sims) / count
    return EmailSimulation(
        email_id=email_id,
        attack_vector=sims[0].attack_vector,
        layers=layers,
        passed=int(round(passed / count)),
        pass_rate=total / pooled if pooled else 0.0,
        ci95=wilson_mean(total, pooled),
        closed_form=form,
    )


def wilson_mean(passed: int, runs: int) -> tuple[float, float]:
    from layersight.simulation.montecarlo import wilson

    return wilson(passed, runs)


def _empty(name: str, vector: str) -> EmailSimulation:
    del name, vector
    from layersight.models import AttackVector

    kind: AttackVector = "credential_harvest"
    return EmailSimulation(
        email_id="aggregate",
        attack_vector=kind,
        layers=[],
        passed=0,
        pass_rate=0.0,
        ci95=(0.0, 0.0),
        closed_form=0.0,
    )


def _pack(
    baseline: LayerConfig,
    other: LayerConfig,
    left: EmailSimulation,
    right: EmailSimulation,
    seed: int,
    runs: int,
) -> EmailComparison:
    base = left.closed_form
    alt = right.closed_form
    relative_closed = 0.0 if base <= 0 else (base - alt) / base
    return EmailComparison(
        baseline=SideResult(config_name=baseline.name, simulation=left),
        comparison=SideResult(config_name=other.name, simulation=right),
        relative_reduction=relative_closed,
        narrative=narrative(baseline, other, base, alt),
        seed=seed,
        runs=runs,
        engine_version=__version__,
    )


def narrative(baseline: LayerConfig, other: LayerConfig, before: float, after: float) -> str:
    change = _change(baseline, other)
    if before <= 0 and after <= 0:
        return f"{change} the modeled pass-through is 0.00%."
    if before <= 0:
        return f"{change} the modeled pass-through is {after * 100:.2f}%."
    relative = (before - after) / before
    if after <= before:
        verb, noun = "reduces", "reduction"
        amount = relative
    else:
        verb, noun = "raises", "increase"
        amount = -relative
    return (
        f"{change} {verb} the modeled chance an attack passes every layer "
        f"from {before * 100:.2f}% to {after * 100:.2f}%, a {amount * 100:.1f}% {noun}."
    )


def _change(baseline: LayerConfig, other: LayerConfig) -> str:
    changes: list[str] = []
    if baseline.user_training.level != other.user_training.level:
        changes.append(
            f"user training from {baseline.user_training.level} to {other.user_training.level}"
        )
    if baseline.email_filter.base_catch_rate != other.email_filter.base_catch_rate:
        changes.append("the email filter")
    if baseline.application_control.effectiveness != other.application_control.effectiveness:
        changes.append("application control")
    if baseline.antivirus.detection_rate != other.antivirus.detection_rate:
        changes.append("antivirus")
    if baseline.segmentation.containment_rate != other.segmentation.containment_rate:
        changes.append("segmentation")
    if len(changes) == 1:
        return f"Improving {changes[0]}, with all other controls unchanged,"
    if not changes:
        return "With no control changed,"
    return "Changing more than one control,"
