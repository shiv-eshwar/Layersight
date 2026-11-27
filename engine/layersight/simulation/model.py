"""Per-email stop probability for each layer, with the reason it came out that way."""

from __future__ import annotations

from layersight.config.schema import LayerConfig, match_feature
from layersight.models import AttackVector, EmailAnalysis, LayerOutcome
from layersight.refs import Assumptions
from layersight.simulation.montecarlo import LAYERS

_APPLIES: dict[AttackVector, tuple[bool, bool, bool, bool, bool]] = {
    "malware_attachment": (True, True, True, True, True),
    "malware_link": (True, True, True, True, True),
    "credential_harvest": (True, True, False, False, True),
    "payment_fraud": (True, True, False, False, False),
}


def layer_probabilities(
    analysis: EmailAnalysis,
    config: LayerConfig,
    assumptions: Assumptions,
) -> list[LayerOutcome]:
    applies = list(_APPLIES[analysis.attack_vector])
    credential = analysis.attack_vector == "credential_harvest"
    if credential and not config.segmentation.applies_to_credential_harvest:
        applies[4] = False
    outcomes: list[LayerOutcome] = []
    for layer, applicable in zip(LAYERS, applies, strict=True):
        if not applicable:
            outcomes.append(
                LayerOutcome(
                    layer=layer,  # type: ignore[arg-type]
                    applicable=False,
                    p_stop=0.0,
                    reasons=[f"Not applicable to {analysis.attack_vector.replace('_', ' ')}."],
                    entered=0,
                    stopped=0,
                )
            )
            continue
        probability, reasons = _probability(layer, analysis, config, assumptions)
        outcomes.append(
            LayerOutcome(
                layer=layer,  # type: ignore[arg-type]
                applicable=True,
                p_stop=probability,
                reasons=reasons,
                entered=0,
                stopped=0,
            )
        )
    return outcomes


def _probability(
    layer: str,
    analysis: EmailAnalysis,
    config: LayerConfig,
    assumptions: Assumptions,
) -> tuple[float, list[str]]:
    if layer == "email_filter":
        keep = 1.0 - config.email_filter.base_catch_rate
        reasons = [f"Base catch rate {config.email_filter.base_catch_rate:.2f}."]
        for rule in config.email_filter.rules:
            if rule.enabled and match_feature(analysis.features, rule.match):
                keep *= 1.0 - rule.catch_rate
                reasons.append(f"Rule {rule.id} matched ({rule.catch_rate:.2f}).")
        if len(reasons) == 1:
            reasons.append("No filter rules matched.")
        return 1.0 - keep, reasons
    if layer == "user":
        training = config.user_training
        if training.catch_rate is not None:
            return training.catch_rate, [f"Catch rate override {training.catch_rate:.2f}."]
        level = assumptions.training[training.level]
        raw = level.base + level.sensitivity * (analysis.cue_score - 0.5)
        low, high = assumptions.user_clamp
        probability = min(high, max(low, raw))
        return (
            probability,
            [
                f"Training level {training.level}, cue score {analysis.cue_score:.2f}, "
                f"catch rate {probability:.2f}."
            ],
        )
    if layer == "application_control":
        risk = str(analysis.features.get("attachment.risk_class") or "")
        override = config.application_control.overrides.get(risk)
        if override is not None:
            return float(override), [f"Override for {risk} attachments ({float(override):.2f})."]
        rate = config.application_control.effectiveness
        return rate, [f"Effectiveness {rate:.2f}."]
    if layer == "antivirus":
        rate = config.antivirus.detection_rate
        archive = analysis.features.get("attachment.risk_class") == "archive"
        if archive and analysis.features.get("attachment.password_in_body"):
            rate *= assumptions.antivirus_password_factor
            return rate, [
                f"Detection {config.antivirus.detection_rate:.2f}, "
                "halved because the archive mentions a password."
            ]
        return rate, [f"Detection rate {rate:.2f}."]
    rate = config.segmentation.containment_rate
    return rate, [f"Containment rate {rate:.2f}."]
