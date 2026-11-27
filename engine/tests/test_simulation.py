"""Phase 2: the illustrative scenario, both configs, and the simulation invariants."""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from layersight.config.adapter import ConfigError, load_config
from layersight.config.schema import LayerConfig
from layersight.models import EmailAnalysis
from layersight.refs import assumptions
from layersight.simulation.analytic import expected_remaining, round_half_up
from layersight.simulation.compare import compare_email, narrative, simulate
from layersight.simulation.model import layer_probabilities
from layersight.simulation.montecarlo import closed_form, run, uniforms
from layersight.simulation.recommend import build_recommendations

ROOT = Path(__file__).resolve().parents[2]
CONFIGS = ROOT / "data" / "dev" / "configs"
SHA = "ab" * 32

ILLUSTRATIVE = (
    "Improving user training from none to advanced, with all other controls unchanged, "
    "reduces the modeled chance an attack passes every layer "
    "from 9.21% to 3.29%, a 64.3% reduction."
)


def _email(**overrides: object) -> EmailAnalysis:
    payload: dict[str, object] = {
        "email_id": "golden-malware",
        "risk_score": 0.91,
        "label": "phishing",
        "band": "critical",
        "attack_vector": "malware_attachment",
        "vector_reason": "Illustrative malware attachment with a neutral cue score.",
        "evidence": [],
        "advice": [],
        "cue_score": 0.5,
        "features": {
            "auth.dmarc": "pass",
            "attachment.risk_class": "other",
            "attachment.password_in_body": False,
            "links.max_lookalike_score": 0.1,
        },
        "engine_version": "0.1.0",
        "weights_hash": "stub",
    }
    payload.update(overrides)
    return EmailAnalysis.model_validate(payload)


def _configs() -> tuple[LayerConfig, LayerConfig]:
    untrained, warnings_a = load_config(CONFIGS / "untrained.yaml")
    trained, warnings_b = load_config(CONFIGS / "trained.yaml")
    assert warnings_a == []
    assert warnings_b == []
    return untrained, trained


def test_both_dev_configs_load() -> None:
    untrained, trained = _configs()
    assert untrained.user_training.level == "none"
    assert trained.user_training.level == "advanced"
    assert untrained.email_filter.base_catch_rate == pytest.approx(0.35)
    assert trained.antivirus.detection_rate == pytest.approx(0.55)


def test_illustrative_stop_rates_and_closed_form() -> None:
    untrained, trained = _configs()
    email = _email()
    table = assumptions()
    untrained_p = [layer.p_stop for layer in layer_probabilities(email, untrained, table)]
    trained_p = [layer.p_stop for layer in layer_probabilities(email, trained, table)]
    assert untrained_p == pytest.approx([0.35, 0.30, 0.25, 0.55, 0.40])
    assert trained_p == pytest.approx([0.35, 0.75, 0.25, 0.55, 0.40])
    assert closed_form(untrained_p) == pytest.approx(0.0921375)
    assert closed_form(trained_p) == pytest.approx(0.03290625)
    remaining = [round_half_up(value) for value in expected_remaining(10_000, untrained_p)]
    assert remaining == [6500, 4550, 3413, 1536, 921]


def test_credential_and_payment_skip_endpoint_controls() -> None:
    untrained, _trained = _configs()
    table = assumptions()
    credential = _email(
        email_id="credential",
        attack_vector="credential_harvest",
        features={"auth.dmarc": "pass", "links.max_lookalike_score": 0.1},
    )
    payment = _email(
        email_id="payment",
        attack_vector="payment_fraud",
        band="high",
        risk_score=0.74,
        features={"auth.dmarc": "pass"},
    )
    credential_layers = layer_probabilities(credential, untrained, table)
    payment_layers = layer_probabilities(payment, untrained, table)
    assert [layer.applicable for layer in credential_layers] == [True, True, False, False, True]
    assert [layer.applicable for layer in payment_layers] == [True, True, False, False, False]
    assert credential_layers[3].p_stop == 0
    assert "Not applicable" in credential_layers[3].reasons[0]
    assert closed_form([layer.p_stop for layer in credential_layers]) == pytest.approx(0.273)
    assert closed_form([layer.p_stop for layer in payment_layers]) == pytest.approx(0.455)
    blocked = untrained.model_copy(deep=True)
    blocked.segmentation.applies_to_credential_harvest = False
    again = layer_probabilities(credential, blocked, table)
    assert again[4].applicable is False
    assert again[4].p_stop == 0


def test_matched_rules_and_password_archive() -> None:
    untrained, _trained = _configs()
    table = assumptions()
    hostile = _email(
        features={
            "auth.dmarc": "fail",
            "attachment.risk_class": "executable",
            "attachment.password_in_body": False,
        }
    )
    layers = layer_probabilities(hostile, untrained, table)
    assert layers[0].p_stop == pytest.approx(1 - 0.65 * 0.15 * 0.02)
    assert layers[2].p_stop == pytest.approx(0.95)
    archive = _email(
        features={
            "auth.dmarc": "pass",
            "attachment.risk_class": "archive",
            "attachment.password_in_body": True,
        }
    )
    antivirus = layer_probabilities(archive, untrained, table)[3]
    assert antivirus.p_stop == pytest.approx(0.275)
    assert any("halved" in reason for reason in antivirus.reasons)


def test_narrative_matches_the_illustrative_sentence() -> None:
    untrained, trained = _configs()
    email = _email()
    result = compare_email(email, SHA, untrained, trained, runs=10_000, seed=42)
    assert result.baseline.simulation.closed_form == pytest.approx(0.0921375)
    assert result.comparison.simulation.closed_form == pytest.approx(0.03290625)
    assert result.narrative == ILLUSTRATIVE
    low, high = result.baseline.simulation.ci95
    assert low <= result.baseline.simulation.closed_form <= high
    low_b, high_b = result.comparison.simulation.ci95
    assert low_b <= result.comparison.simulation.closed_form <= high_b


def test_same_seed_is_identical_and_order_does_not_matter() -> None:
    untrained, _trained = _configs()
    first = _email(email_id="one")
    second = _email(email_id="two", attack_vector="credential_harvest")
    left = simulate(first, SHA, untrained, runs=1000, seed=7)
    again = simulate(first, SHA, untrained, runs=1000, seed=7)
    assert left.model_dump() == again.model_dump()
    forward = [
        simulate(first, "11" * 32, untrained, runs=500, seed=3).closed_form,
        simulate(second, "22" * 32, untrained, runs=500, seed=3).closed_form,
    ]
    backward = [
        simulate(second, "22" * 32, untrained, runs=500, seed=3).closed_form,
        simulate(first, "11" * 32, untrained, runs=500, seed=3).closed_form,
    ]
    assert forward == [backward[1], backward[0]]


def test_common_random_numbers_never_increase_passes() -> None:
    untrained, _trained = _configs()
    email = _email()
    draws = uniforms(42, SHA, 4000)
    before = simulate(email, SHA, untrained, runs=4000, seed=42, draws=draws)
    stronger = untrained.model_copy(deep=True)
    stronger.user_training.catch_rate = 0.9
    after = simulate(email, SHA, stronger, runs=4000, seed=42, draws=draws)
    assert after.passed <= before.passed
    assert after.closed_form < before.closed_form


def test_training_is_the_top_recommendation_and_antivirus_misses_credential_theft() -> None:
    untrained, _trained = _configs()
    malware = _email()
    credential = _email(email_id="credential", attack_vector="credential_harvest")
    report = build_recommendations([malware, credential, credential], untrained)
    assert report.recommendations[0].id == "next_training_level"
    credential_ids = {item.id for item in build_recommendations([credential], untrained).recommendations}
    assert "better_antivirus" not in credential_ids
    user = next(bar for bar in report.sensitivity if bar.layer == "user")
    antivirus = next(bar for bar in report.sensitivity if bar.layer == "antivirus")
    credential_only = build_recommendations([credential], untrained)
    antivirus_only = next(bar for bar in credential_only.sensitivity if bar.layer == "antivirus")
    assert user.swing > antivirus.swing
    assert antivirus_only.swing == 0


def test_unknown_config_key_warns_and_bad_rate_names_the_field(tmp_path: Path) -> None:
    loose = tmp_path / "loose.yaml"
    loose.write_text(
        "name: Loose\n"
        "email_filter_catch_rate: 35%\n"
        "user_training: trained\n"
        "application_control: 25%\n"
        "antivirus: 55%\n"
        "segmentation: 40%\n"
        "vendor_notes: ignore me\n",
        encoding="utf-8",
    )
    config, warnings = load_config(loose)
    assert config.user_training.level == "advanced"
    assert config.email_filter.base_catch_rate == pytest.approx(0.35)
    assert any("vendor_notes" in warning for warning in warnings)
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        "schema_version: 1\n"
        "name: Broken\n"
        "email_filter: {base_catch_rate: 1.5}\n"
        "user_training: {level: none}\n"
        "application_control: {effectiveness: 0.25}\n"
        "antivirus: {detection_rate: 0.55}\n"
        "segmentation: {containment_rate: 0.40}\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError) as exc:
        load_config(broken)
    assert "base_catch_rate" in exc.value.detail


def test_narrative_helper_uses_closed_form() -> None:
    untrained, trained = _configs()
    sentence = narrative(untrained, trained, 0.0921375, 0.03290625)
    assert sentence == ILLUSTRATIVE


@given(
    p_stop=st.lists(st.floats(min_value=0, max_value=1, allow_nan=False), min_size=5, max_size=5)
)
@settings(max_examples=30, deadline=None, derandomize=True)
def test_raising_any_layer_never_raises_the_closed_form(p_stop: list[float]) -> None:
    base = closed_form(p_stop)
    for index in range(5):
        raised = list(p_stop)
        raised[index] = min(1.0, raised[index] + 0.1)
        assert closed_form(raised) <= base + 1e-12


def test_monte_carlo_counts_cover_every_run() -> None:
    import numpy as np

    draws = uniforms(1, SHA, 1000)
    counts = run(np.array([0.2, 0.0, 1.0, 0.0, 0.0]), draws)
    assert int(counts.sum()) == 1000
    assert int(counts[1]) == 0
