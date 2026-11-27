"""Modeled residual risk for the command center.

Layer rates follow engineering.md. Counts are model estimates, not measurements.
Quiz accuracy can replace the user-layer catch rate. It does not change the other layers.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path

import yaml

from layersight import __version__
from layersight.models import EmailAnalysis
from layersight.phase6.models import (
    CommandCenter,
    DatasetSummary,
    FunnelStep,
    Outlook,
    RecommendationView,
    ThreatRow,
    UncertaintyBand,
)
from layersight.phase6.records import ScoredMail

_CONFIGS = Path(__file__).resolve().parents[3] / "data" / "dev" / "configs"
_LAYERS = ("email_filter", "user", "application_control", "antivirus", "segmentation")
_LAYER_LABELS = {
    "email_filter": "Email filter",
    "user": "User",
    "application_control": "Application control",
    "antivirus": "Antivirus",
    "segmentation": "Segmentation",
    "passed": "Passed every layer",
}
_TRAINING = {"none": (0.30, 0.10), "basic": (0.55, 0.25), "advanced": (0.75, 0.35)}
_NEXT = {"none": "basic", "basic": "advanced"}
_CLAMP = (0.02, 0.98)
_NOTE = (
    "Figures are model estimates from the assumptions shown, not measured outcomes. "
    "Labels are used for accuracy and the quiz only. They are not an input to the score."
)


@dataclass(frozen=True)
class FilterRule:
    id: str
    feature: str
    op: str
    value: str | float | tuple[str, ...] | None
    catch_rate: float
    enabled: bool = True


@dataclass(frozen=True)
class Defense:
    name: str
    org_domains: tuple[str, ...]
    filter_base: float
    rules: tuple[FilterRule, ...]
    training_level: str
    user_catch_rate: float | None
    app_effectiveness: float
    app_overrides: tuple[tuple[str, float], ...]
    antivirus: float
    segmentation: float
    segmentation_credential: bool
    runs: int
    seed: int


def load_pair(directory: Path | None = None) -> tuple[Defense, Defense]:
    root = directory or _CONFIGS
    before = _read_config(root / "untrained.yaml") if (root /
                                                       "untrained.yaml").is_file() else _bare("Untrained users (v1)", "none")  # noqa: E501
    if (root / "trained.yaml").is_file():
        after = _read_config(root / "trained.yaml")
    else:
        after = _copy(before, name="Trained users (v2)",
                      training_level="advanced", user_catch_rate=None)
    return before, after


def command_center(
    dataset_id: str,
    name: str,
    mails: list[ScoredMail],
    before: Defense,
    trained: Defense,
    user_catch_rate: float | None = None,
) -> CommandCenter:
    current_after = trained
    source = "config"
    if user_catch_rate is not None:
        current_after = _copy(
            before,
            name="Quiz-measured users",
            user_catch_rate=user_catch_rate,
        )
        source = "quiz"
    phishing = [mail for mail in mails if mail.analysis.label == "phishing"]
    before_view = _outlook(before, phishing)
    after_view = _outlook(current_after, phishing)
    trained_view = _outlook(trained, phishing)
    labeled = [mail for mail in mails if mail.true_label in {"phishing", "genuine"}]
    correct = sum(1 for mail in labeled if mail.true_label == mail.analysis.label)
    accuracy = (correct / len(labeled)) if labeled else None
    reduction = _relative(before_view.closed_form, after_view.closed_form)
    summary = DatasetSummary(
        dataset_id=dataset_id,
        name=name,
        email_count=len(mails),
        phishing_count=sum(1 for mail in mails if mail.analysis.label == "phishing"),
        genuine_count=sum(1 for mail in mails if mail.analysis.label == "genuine"),
        accuracy=accuracy,
        correct=correct if labeled else None,
        labeled=len(labeled) if labeled else None,
        pass_rate_before=before_view.closed_form,
        pass_rate_after=after_view.closed_form,
        relative_reduction=reduction,
    )
    return CommandCenter(
        summary=summary,
        before=before_view,
        after=after_view,
        trained_pass_rate=trained_view.closed_form,
        recommendation=_recommend(before, phishing),
        threats=_threats(mails),
        brands=[],
        user_layer_source=source,  # type: ignore[arg-type]
        user_catch_rate=user_catch_rate,
        engine_version=__version__,
        seed=before.seed,
        note=_NOTE,
    )


def closed_form(probabilities: list[float]) -> float:
    product = 1.0
    for probability in probabilities:
        product *= 1.0 - probability
    return product


def funnel_entered(probabilities: list[float], runs: int) -> list[int]:
    """Remaining attacks after each layer, rounded half up from the original run count."""
    survival = 1.0
    entered = [runs]
    for probability in probabilities:
        survival *= 1.0 - probability
        entered.append(_round_half_up(runs * survival))
    return entered


def _outlook(config: Defense, phishing: list[ScoredMail]) -> Outlook:
    if not phishing:
        return Outlook(name=config.name, runs=config.runs, funnel=[])
    curves = [_stop_probabilities(mail.analysis, config) for mail in phishing]
    forms = [closed_form(curve) for curve in curves]
    mean_form = sum(forms) / len(forms)
    entered = _mean_entered(curves, config.runs)
    steps: list[FunnelStep] = []
    for index, layer in enumerate(_LAYERS):
        steps.append(
            FunnelStep(
                layer=layer,
                label=_LAYER_LABELS[layer],
                entered=entered[index],
                stopped=max(0, entered[index] - entered[index + 1]),
            )
        )
    passed = entered[-1]
    steps.append(
        FunnelStep(layer="passed", label=_LAYER_LABELS["passed"], entered=passed, stopped=0)
    )
    blocked = max(0, config.runs - passed)
    band = _uncertainty(curves, config.seed)
    return Outlook(
        name=config.name,
        pass_rate=passed / config.runs,
        blocked_rate=blocked / config.runs,
        passed=passed,
        blocked=blocked,
        runs=config.runs,
        closed_form=mean_form,
        funnel=steps,
        uncertainty=band,
    )


def _mean_entered(curves: list[list[float]], runs: int) -> list[int]:
    totals = [0.0] * (len(_LAYERS) + 1)
    for curve in curves:
        survival = 1.0
        totals[0] += runs
        for index, probability in enumerate(curve):
            survival *= 1.0 - probability
            totals[index + 1] += runs * survival
    return [_round_half_up(value / len(curves)) for value in totals]


def _stop_probabilities(analysis: EmailAnalysis, config: Defense) -> list[float]:
    applicable = _applicable(analysis.attack_vector, config)
    extras = [rule.catch_rate for rule in config.rules if rule.enabled and _matches(
        rule, analysis.features)]
    filter_p = _noisy_or(config.filter_base, extras) if applicable[0] else 0.0
    user_p = _user_probability(analysis.cue_score, config) if applicable[1] else 0.0
    risk_class = analysis.features.get("attachment.risk_class")
    overrides = dict(config.app_overrides)
    if applicable[2]:
        app_p = overrides.get(str(risk_class), config.app_effectiveness)
    else:
        app_p = 0.0
    if applicable[3]:
        av_p = config.antivirus
        if analysis.features.get("attachment.password_protected") is True:
            av_p *= 0.5
    else:
        av_p = 0.0
    seg_p = config.segmentation if applicable[4] else 0.0
    return [filter_p, user_p, app_p, av_p, seg_p]


def _applicable(vector: str, config: Defense) -> tuple[bool, bool, bool, bool, bool]:
    if vector in {"malware_attachment", "malware_link"}:
        return (True, True, True, True, True)
    if vector == "credential_harvest":
        return (True, True, False, False, config.segmentation_credential)
    return (True, True, False, False, False)


def _user_probability(cue: float, config: Defense) -> float:
    if config.user_catch_rate is not None:
        return _clamp(config.user_catch_rate)
    base, sensitivity = _TRAINING.get(config.training_level, _TRAINING["none"])
    return _clamp(base + sensitivity * (cue - 0.5))


def _matches(rule: FilterRule, features: dict[str, object]) -> bool:
    if rule.op == "exists":
        return rule.feature in features and features[rule.feature] not in (None, "", False)
    if rule.feature not in features:
        return False
    raw = features[rule.feature]
    if rule.op == "eq":
        return raw == rule.value
    if rule.op == "ne":
        return raw != rule.value
    if rule.op == "in" and isinstance(rule.value, tuple):
        return raw in rule.value
    if rule.op in {"gte", "lte"} and isinstance(raw, (int, float)) and not isinstance(raw, bool):
        if not isinstance(rule.value, (int, float)):
            return False
        return float(raw) >= float(rule.value) if rule.op == "gte" else float(raw) <= float(rule.value)  # noqa: E501
    if rule.op == "contains" and isinstance(raw, str) and isinstance(rule.value, str):
        return rule.value in raw
    return False


def _noisy_or(base: float, extras: list[float]) -> float:
    product = 1.0 - base
    for catch in extras:
        product *= 1.0 - catch
    return 1.0 - product


def _recommend(config: Defense, phishing: list[ScoredMail]) -> RecommendationView | None:
    if not phishing:
        return None
    baseline = _mean_form(phishing, config)
    candidates: list[tuple[float, RecommendationView]] = []
    nxt = _NEXT.get(config.training_level)
    if nxt and config.user_catch_rate is None:
        changed = _copy(config, training_level=nxt)
        candidates.append(_pack("raise_training", "user", config, changed, phishing, baseline, nxt))
    if not any(rule.feature == "auth.dmarc" and rule.op == "eq" for rule in config.rules):
        rule = FilterRule("quarantine_dmarc_fail", "auth.dmarc", "eq", "fail", 0.85)
        changed = _copy(config, rules=config.rules + (rule,))
        candidates.append(
            _pack("quarantine_dmarc", "email_filter", config,
                  changed, phishing, baseline, "DMARC quarantine")
        )
    if not any(rule.feature == "links.max_lookalike_score" for rule in config.rules):
        rule = FilterRule("lookalike_filter", "links.max_lookalike_score", "gte", 0.85, 0.90)
        changed = _copy(config, rules=config.rules + (rule,))
        candidates.append(
            _pack("lookalike_filter", "email_filter", config,
                  changed, phishing, baseline, "look-alike filter")
        )
    overrides = dict(config.app_overrides)
    if overrides.get("macro_document", 0.0) < 0.90:
        overrides["macro_document"] = 0.90
        changed = _copy(config, app_overrides=tuple(overrides.items()))
        candidates.append(
            _pack("block_macros", "application_control", config,
                  changed, phishing, baseline, "macro blocking")
        )
    if config.antivirus < 0.98:
        changed = _copy(config, antivirus=min(0.98, config.antivirus + 0.15))
        candidates.append(
            _pack("better_antivirus", "antivirus", config, changed,
                  phishing, baseline, "endpoint detection")
        )
    if config.segmentation < 0.98:
        changed = _copy(config, segmentation=min(0.98, config.segmentation + 0.20))
        candidates.append(
            _pack("tighter_segmentation", "segmentation", config,
                  changed, phishing, baseline, "segmentation")
        )
    useful = [item for item in candidates if item[0] > 1e-4]
    if not useful:
        return None
    useful.sort(key=lambda item: item[0], reverse=True)
    return useful[0][1]


def _pack(
    ident: str,
    layer: str,
    before: Defense,
    after: Defense,
    phishing: list[ScoredMail],
    baseline: float,
    change: str,
) -> tuple[float, RecommendationView]:
    updated = _mean_form(phishing, after)
    absolute = baseline - updated
    relative = _relative(baseline, updated) or 0.0
    helped = []
    for mail in phishing:
        if closed_form(_stop_probabilities(mail.analysis, after)) + 1e-9 < closed_form(
            _stop_probabilities(mail.analysis, before)
        ):
            if mail.analysis.attack_vector not in helped:
                helped.append(mail.analysis.attack_vector)
    title = f"Change {change}"
    if ident == "raise_training":
        title = f"Advance user training from {before.training_level} to {after.training_level}"
    detail = (
        f"Modeled pass-through falls from {_pct(baseline)} to {_pct(updated)}, "
        f"a {_pct(relative, 1)} reduction, with the other controls unchanged."
    )
    return absolute, RecommendationView(
        id=ident,
        title=title,
        detail=detail,
        layer=layer,
        absolute_reduction=absolute,
        relative_reduction=relative,
        vectors_helped=helped,
    )


def _mean_form(phishing: list[ScoredMail], config: Defense) -> float:
    return sum(closed_form(_stop_probabilities(mail.analysis, config)) for mail in phishing) / len(phishing)  # noqa: E501


def _threats(mails: list[ScoredMail]) -> list[ThreatRow]:
    ordered = sorted(mails, key=lambda mail: mail.analysis.risk_score, reverse=True)[:5]
    rows: list[ThreatRow] = []
    for mail in ordered:
        top = next((item.detail for item in mail.analysis.evidence if item.contribution > 0), None)
        rows.append(
            ThreatRow(
                email_id=mail.email_id,
                subject=mail.subject or "(no subject)",
                sender=mail.sender or mail.observed.sender_address,
                risk_score=mail.analysis.risk_score,
                band=mail.analysis.band,
                label=mail.analysis.label,
                attack_vector=mail.analysis.attack_vector,
                top_evidence=top,
            )
        )
    return rows


def _uncertainty(curves: list[list[float]], seed: int) -> UncertaintyBand:
    rng = random.Random(seed)
    draws = 2000
    kappa = 50.0
    samples: list[float] = []
    for _ in range(draws):
        total = 0.0
        for curve in curves:
            product = 1.0
            for probability in curve:
                if probability <= 0:
                    continue
                mean = min(max(probability, 0.02), 0.98)
                product *= 1.0 - rng.betavariate(mean * kappa, (1.0 - mean) * kappa)
            total += product
        samples.append(total / len(curves))
    samples.sort()
    return UncertaintyBand(
        p05=_percentile(samples, 0.05),
        p50=_percentile(samples, 0.50),
        p95=_percentile(samples, 0.95),
        kappa=kappa,
    )


def _percentile(samples: list[float], quantile: float) -> float:
    if not samples:
        return 0.0
    index = min(len(samples) - 1, max(0, int(round(quantile * (len(samples) - 1)))))
    return samples[index]


def _relative(before: float | None, after: float | None) -> float | None:
    if before is None or after is None or before <= 1e-12:
        return None
    return (before - after) / before


def _pct(value: float, digits: int = 2) -> str:
    return f"{value * 100:.{digits}f}%"


def _clamp(value: float) -> float:
    return min(_CLAMP[1], max(_CLAMP[0], value))


def _round_half_up(value: float) -> int:
    # The extra millionth absorbs binary fractions such as 0.65 * 0.70 * 0.75.
    return int(math.floor(value + 0.5 + 1e-6))


def _copy(config: Defense, **changes: object) -> Defense:
    data = {
        "name": config.name,
        "org_domains": config.org_domains,
        "filter_base": config.filter_base,
        "rules": config.rules,
        "training_level": config.training_level,
        "user_catch_rate": config.user_catch_rate,
        "app_effectiveness": config.app_effectiveness,
        "app_overrides": config.app_overrides,
        "antivirus": config.antivirus,
        "segmentation": config.segmentation,
        "segmentation_credential": config.segmentation_credential,
        "runs": config.runs,
        "seed": config.seed,
    }
    data.update(changes)
    return Defense(**data)  # type: ignore[arg-type]


def _bare(name: str, level: str) -> Defense:
    return Defense(
        name=name,
        org_domains=("contoso.example",),
        filter_base=0.35,
        rules=(),
        training_level=level,
        user_catch_rate=None,
        app_effectiveness=0.25,
        app_overrides=(),
        antivirus=0.55,
        segmentation=0.40,
        segmentation_credential=True,
        runs=10_000,
        seed=42,
    )


def _read_config(path: Path) -> Defense:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return _bare(path.stem, "none")
    filt = raw.get("email_filter") if isinstance(raw.get("email_filter"), dict) else {}
    user = raw.get("user_training") if isinstance(raw.get("user_training"), dict) else {}
    app = raw.get("application_control") if isinstance(raw.get("application_control"), dict) else {}
    antivirus = raw.get("antivirus") if isinstance(raw.get("antivirus"), dict) else {}
    seg = raw.get("segmentation") if isinstance(raw.get("segmentation"), dict) else {}
    sim = raw.get("simulation") if isinstance(raw.get("simulation"), dict) else {}
    rules: list[FilterRule] = []
    for item in filt.get("rules", []) if isinstance(filt, dict) else []:
        if not isinstance(item, dict):
            continue
        match = item.get("match") if isinstance(item.get("match"), dict) else {}
        value = match.get("value")
        if isinstance(value, list):
            stored: str | float | tuple[str, ...] | None = tuple(str(part) for part in value)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            stored = float(value)
        elif value is None:
            stored = None
        else:
            stored = str(value)
        rules.append(
            FilterRule(
                id=str(item.get("id") or "rule"),
                feature=str(match.get("feature") or ""),
                op=str(match.get("op") or "eq"),
                value=stored,
                catch_rate=float(item.get("catch_rate") or 0),
                enabled=bool(item.get("enabled", True)),
            )
        )
    overrides_raw = app.get("overrides") if isinstance(app, dict) else {}
    overrides = tuple(
        (str(key), float(value))
        for key, value in overrides_raw.items()
        if isinstance(overrides_raw, dict)
    ) if isinstance(overrides_raw, dict) else ()
    orgs = tuple(str(item) for item in raw.get("org_domains", [])
                 if isinstance(raw.get("org_domains"), list))
    level = str(user.get("level") or "none") if isinstance(user, dict) else "none"
    catch = user.get("catch_rate") if isinstance(user, dict) else None
    return Defense(
        name=str(raw.get("name") or path.stem),
        org_domains=orgs or ("contoso.example",),
        filter_base=float(filt.get("base_catch_rate", 0.35)) if isinstance(filt, dict) else 0.35,
        rules=tuple(rules),
        training_level=level,
        user_catch_rate=float(catch) if isinstance(
            catch, (int, float)) and not isinstance(catch, bool) else None,
        app_effectiveness=float(app.get("effectiveness", 0.25)) if isinstance(app, dict) else 0.25,
        app_overrides=overrides,
        antivirus=float(antivirus.get("detection_rate", 0.55)
                        ) if isinstance(antivirus, dict) else 0.55,
        segmentation=float(seg.get("containment_rate", 0.40)) if isinstance(seg, dict) else 0.40,
        segmentation_credential=bool(
            seg.get("applies_to_credential_harvest", True)) if isinstance(seg, dict) else True,
        runs=int(sim.get("runs", 10_000)) if isinstance(sim, dict) else 10_000,
        seed=int(sim.get("seed", 42)) if isinstance(sim, dict) else 42,
    )
