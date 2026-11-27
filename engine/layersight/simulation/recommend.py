"""Rank the next control change by how much it cuts modeled pass-through.

The ranking uses the closed form, so it does not move between seeds.
A layer that cannot see an attack does not get credit for being stronger.
"""

from __future__ import annotations

from dataclasses import dataclass

from layersight.config.schema import FilterRule, LayerConfig, Match
from layersight.models import AttackVector, EmailAnalysis, LayerOutcome
from layersight.refs import assumptions
from layersight.simulation.model import layer_probabilities
from layersight.simulation.montecarlo import closed_form

_ORDER: tuple[str, ...] = ("none", "basic", "advanced")
_VECTORS: tuple[AttackVector, ...] = (
    "malware_attachment",
    "malware_link",
    "credential_harvest",
    "payment_fraud",
)


@dataclass(frozen=True)
class Recommendation:
    id: str
    title: str
    detail: str
    absolute_reduction: float
    baseline_pass_rate: float
    pass_rate: float
    vectors_benefiting: tuple[AttackVector, ...]


@dataclass(frozen=True)
class SensitivityBar:
    layer: str
    pass_rate_weaker: float
    pass_rate_stronger: float
    swing: float


@dataclass(frozen=True)
class RecommendationReport:
    baseline_pass_rate: float
    recommendations: tuple[Recommendation, ...]
    sensitivity: tuple[SensitivityBar, ...]


def build_recommendations(emails: list[EmailAnalysis], config: LayerConfig) -> RecommendationReport:
    selected = [email for email in emails if email.label == "phishing"]
    if not selected:
        raise ValueError("No phishing emails to score. Nothing would change.")
    baseline = _mean_pass(selected, config)
    ranked: list[tuple[int, Recommendation]] = []
    for order, built in enumerate(_candidates(config)):
        if built is None:
            continue
        candidate_id, title, updated = built
        rate = _mean_pass(selected, updated)
        reduction = baseline - rate
        if reduction <= 1e-9:
            continue
        vectors = _benefiting(selected, config, updated)
        points = f"{reduction * 100:.2f} percentage points"
        names = _join([vector.replace("_", " ") for vector in vectors])
        detail = (
            f"Lowers the modeled pass-through from {baseline * 100:.2f}% "
            f"to {rate * 100:.2f}%, an absolute reduction of {points}. Helps {names}."
        )
        ranked.append(
            (
                order,
                Recommendation(
                    id=candidate_id,
                    title=title,
                    detail=detail,
                    absolute_reduction=reduction,
                    baseline_pass_rate=baseline,
                    pass_rate=rate,
                    vectors_benefiting=vectors,
                ),
            )
        )
    ranked.sort(key=lambda item: (-item[1].absolute_reduction, item[0]))
    return RecommendationReport(
        baseline_pass_rate=baseline,
        recommendations=tuple(item for _, item in ranked),
        sensitivity=tuple(_sensitivity(selected, config)),
    )


def _candidates(config: LayerConfig) -> list[tuple[str, str, LayerConfig] | None]:
    return [
        _next_training(config),
        _dmarc_rule(config),
        _lookalike_rule(config),
        _block_macros(config),
        _better_antivirus(config),
        _tighter_segmentation(config),
    ]


def _next_training(config: LayerConfig) -> tuple[str, str, LayerConfig] | None:
    level = config.user_training.level
    if level not in _ORDER:
        return None
    index = _ORDER.index(level)
    if index == len(_ORDER) - 1:
        return None
    nxt = _ORDER[index + 1]
    updated = config.model_copy(deep=True)
    updated.user_training.level = nxt  # type: ignore[assignment]
    updated.user_training.catch_rate = None
    title = f"Train users from {level} to {nxt}"
    if config.user_training.catch_rate is not None:
        title += " using the training table"
    return ("next_training_level", title, updated)


def _dmarc_rule(config: LayerConfig) -> tuple[str, str, LayerConfig] | None:
    if _has_match(config, "auth.dmarc", "eq", "fail"):
        return None
    rule = FilterRule(
        id="quarantine_dmarc_fail",
        description="Quarantine messages that fail DMARC",
        match=Match(feature="auth.dmarc", op="eq", value="fail"),
        catch_rate=0.85,
    )
    updated = _with_rule(config, rule)
    return ("quarantine_dmarc_fail", "Quarantine messages that fail DMARC", updated)


def _lookalike_rule(config: LayerConfig) -> tuple[str, str, LayerConfig] | None:
    for rule in config.email_filter.rules:
        match = rule.match
        if (
            rule.enabled
            and match.feature == "links.max_lookalike_score"
            and match.op == "gte"
            and isinstance(match.value, int | float)
            and not isinstance(match.value, bool)
            and float(match.value) <= 0.85
        ):
            return None
    rule = FilterRule(
        id="block_lookalike_links",
        description="Quarantine links that imitate a protected domain",
        match=Match(feature="links.max_lookalike_score", op="gte", value=0.85),
        catch_rate=0.80,
    )
    return ("lookalike_filter", "Filter look-alike links", _with_rule(config, rule))


def _block_macros(config: LayerConfig) -> tuple[str, str, LayerConfig] | None:
    current = config.application_control.overrides.get(
        "macro_document",
        config.application_control.effectiveness,
    )
    if current >= 0.90 - 1e-12:
        return None
    updated = config.model_copy(deep=True)
    overrides = dict(updated.application_control.overrides)
    overrides["macro_document"] = 0.90
    updated.application_control.overrides = overrides
    return ("block_macros", "Block macro-enabled documents", updated)


def _better_antivirus(config: LayerConfig) -> tuple[str, str, LayerConfig] | None:
    updated_rate = min(1.0, config.antivirus.detection_rate + 0.15)
    if updated_rate <= config.antivirus.detection_rate + 1e-12:
        return None
    updated = config.model_copy(deep=True)
    updated.antivirus.detection_rate = updated_rate
    return ("better_antivirus", "Raise antivirus detection by 15 points", updated)


def _tighter_segmentation(config: LayerConfig) -> tuple[str, str, LayerConfig] | None:
    updated_rate = min(1.0, config.segmentation.containment_rate + 0.20)
    if updated_rate <= config.segmentation.containment_rate + 1e-12:
        return None
    updated = config.model_copy(deep=True)
    updated.segmentation.containment_rate = updated_rate
    return ("tighter_segmentation", "Tighten segmentation by 20 points", updated)


def _with_rule(config: LayerConfig, rule: FilterRule) -> LayerConfig:
    updated = config.model_copy(deep=True)
    updated.email_filter.rules = [*updated.email_filter.rules, rule]
    return updated


def _has_match(config: LayerConfig, feature: str, op: str, expected: object) -> bool:
    for rule in config.email_filter.rules:
        match = rule.match
        if not rule.enabled or match.feature != feature or match.op != op:
            continue
        if isinstance(expected, str) and isinstance(match.value, str):
            if match.value.casefold() == expected.casefold():
                return True
        elif match.value == expected:
            return True
    return False


def _mean_pass(emails: list[EmailAnalysis], config: LayerConfig) -> float:
    table = assumptions()
    total = 0.0
    for email in emails:
        probabilities = [layer.p_stop for layer in layer_probabilities(email, config, table)]
        total += closed_form(probabilities)
    return total / len(emails)


def _benefiting(
    emails: list[EmailAnalysis],
    before: LayerConfig,
    after: LayerConfig,
) -> tuple[AttackVector, ...]:
    found: list[AttackVector] = []
    for vector in _VECTORS:
        group = [email for email in emails if email.attack_vector == vector]
        if not group:
            continue
        if _mean_pass(group, before) - _mean_pass(group, after) > 1e-9:
            found.append(vector)
    return tuple(found)


def _sensitivity(emails: list[EmailAnalysis], config: LayerConfig) -> list[SensitivityBar]:
    table = assumptions()
    base = [layer_probabilities(email, config, table) for email in emails]
    bars: list[SensitivityBar] = []
    names = ("email_filter", "user", "application_control", "antivirus", "segmentation")
    for index, name in enumerate(names):
        weaker = _shifted(base, index, -0.10)
        stronger = _shifted(base, index, 0.10)
        bars.append(
            SensitivityBar(
                layer=name,
                pass_rate_weaker=weaker,
                pass_rate_stronger=stronger,
                swing=abs(weaker - stronger),
            )
        )
    return bars


def _shifted(rows: list[list[LayerOutcome]], index: int, delta: float) -> float:
    total = 0.0
    for layers in rows:
        rates = [layer.p_stop for layer in layers]
        if layers[index].applicable:
            rates[index] = min(1.0, max(0.0, rates[index] + delta))
        total += closed_form(rates)
    return total / len(rows)


def _join(parts: list[str]) -> str:
    if not parts:
        return "no attack vector in this set"
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return ", ".join(parts[:-1]) + ", and " + parts[-1]
