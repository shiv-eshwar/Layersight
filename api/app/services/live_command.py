"""Command center for a dataset stored by the API.

Pass-through comes from the same simulation the reports page uses, so the
landing screen and the comparison show one set of numbers.
"""

from __future__ import annotations

from app.db import session as open_session
from app.services import get_config, parse_config, recommend_dataset, simulate_dataset
from app.services.phase6_store import get_store
from layersight import __version__
from layersight.phase6.aggregate import brand_rows, domain_report
from layersight.phase6.models import (
    CommandCenter,
    DatasetSummary,
    FunnelStep,
    Outlook,
    RecommendationView,
    ThreatRow,
)

_LABELS = {
    "email_filter": "Email filter",
    "user": "User",
    "application_control": "Application control",
    "antivirus": "Antivirus",
    "segmentation": "Segmentation",
    "passed": "Passed every layer",
}
_NOTE = (
    "Figures are model estimates from the assumptions shown, not measured outcomes. "
    "Labels are used for accuracy and the quiz only. They are not an input to the score."
)


def command_for_dataset(dataset_id: str) -> CommandCenter | None:
    store = get_store()
    if store.get(dataset_id) is not None:
        return None
    dataset = store.resolve(dataset_id)
    if dataset is None:
        return None
    db = next(open_session())
    try:
        before = simulate_dataset(db, dataset_id, "untrained", runs=10000, seed=42, persist=False)
        rate = dataset.user_catch_rate
        after_config = None
        if rate is not None:
            base = parse_config(get_config(db, "untrained")["config"])
            after_config = base.model_copy(
                update={
                    "name": "Quiz-measured users",
                    "user_training": base.user_training.model_copy(
                        update={"catch_rate": rate, "level": "none"}
                    ),
                }
            )
        after = simulate_dataset(
            db,
            dataset_id,
            None if after_config is not None else "trained",
            runs=10000,
            seed=42,
            persist=False,
            config=after_config,
        )
        trained = simulate_dataset(db, dataset_id, "trained", runs=10000, seed=42, persist=False)
        advice = recommend_dataset(db, dataset_id, "untrained")
    finally:
        db.close()

    before_rate = float(before["aggregate"]["closed_form"])
    after_rate = float(after["aggregate"]["closed_form"])
    reduction = 0.0 if before_rate <= 0 else (before_rate - after_rate) / before_rate
    labeled = [mail for mail in dataset.mails if mail.true_label in {"phishing", "genuine"}]
    correct = sum(1 for mail in labeled if mail.true_label == mail.analysis.label)
    ranked = sorted(dataset.mails, key=lambda mail: mail.analysis.risk_score, reverse=True)
    threats = [
        ThreatRow(
            email_id=mail.email_id,
            subject=mail.subject,
            sender=mail.sender,
            risk_score=mail.analysis.risk_score,
            band=mail.analysis.band,
            label=mail.analysis.label,
            attack_vector=mail.analysis.attack_vector,
            top_evidence=mail.analysis.evidence[0].title if mail.analysis.evidence else None,
        )
        for mail in ranked[:5]
    ]
    first = advice["recommendations"][0] if advice["recommendations"] else None
    recommendation = RecommendationView.model_validate(first) if first is not None else None
    brands = brand_rows(domain_report(dataset.id, dataset.mails, list(dataset.before.org_domains)))
    summary = DatasetSummary(
        dataset_id=dataset.id,
        name=dataset.name,
        email_count=len(dataset.mails),
        phishing_count=sum(1 for mail in dataset.mails if mail.analysis.label == "phishing"),
        genuine_count=sum(1 for mail in dataset.mails if mail.analysis.label == "genuine"),
        accuracy=(correct / len(labeled)) if labeled else None,
        correct=correct if labeled else None,
        labeled=len(labeled) if labeled else None,
        pass_rate_before=before_rate,
        pass_rate_after=after_rate,
        relative_reduction=reduction,
    )
    return CommandCenter(
        summary=summary,
        before=_outlook(str(before["config_snapshot"]["name"]), before),
        after=_outlook(str(after["config_snapshot"]["name"]), after),
        trained_pass_rate=float(trained["aggregate"]["closed_form"]),
        recommendation=recommendation,
        threats=threats,
        brands=brands,
        user_layer_source="quiz" if rate is not None else "config",
        user_catch_rate=rate,
        engine_version=__version__,
        seed=42,
        note=_NOTE,
    )


def _outlook(name: str, simulation: dict[str, object]) -> Outlook:
    aggregate = simulation["aggregate"]
    assert isinstance(aggregate, dict)
    runs = int(aggregate["runs"])
    layers = aggregate["layers"]
    assert isinstance(layers, list)
    steps: list[FunnelStep] = []
    for layer in layers:
        assert isinstance(layer, dict)
        key = str(layer["layer"])
        steps.append(
            FunnelStep(
                layer=key,
                label=_LABELS.get(key, key),
                entered=int(layer["entered"]),
                stopped=int(layer["stopped"]),
            )
        )
    passed = 0
    if layers:
        last = layers[-1]
        assert isinstance(last, dict)
        passed = max(0, int(last["entered"]) - int(last["stopped"]))
    steps.append(FunnelStep(layer="passed", label=_LABELS["passed"], entered=passed, stopped=0))
    return Outlook(
        name=name,
        pass_rate=float(aggregate["pass_rate"]),
        blocked_rate=float(aggregate["blocked_rate"]),
        passed=passed,
        blocked=max(0, runs - passed),
        runs=runs,
        closed_form=float(aggregate["closed_form"]),
        funnel=steps,
        uncertainty=None,
    )
