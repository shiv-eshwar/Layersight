"""Illustrative contract payloads.

These are shaped examples for the web shell and for contract tests.
The 9.21% / 3.29% figures are the worked scenario from context.md, not a
measurement of any real organization. Run this module to refresh the JSON
files under contracts/mocks.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from layersight.models import (
    CONTRACT_VERSION,
    ENGINE_VERSION,
    AggregateLayer,
    AggregateSimulation,
    AntivirusConfig,
    ApplicationControlConfig,
    AttachmentRiskClass,
    AttackVector,
    AuthResults,
    AuthStatus,
    ComparisonResult,
    ConfigChange,
    ConfusionMatrix,
    DatasetSummary,
    DomainRecord,
    EmailAnalysis,
    EmailComparison,
    EmailFilterConfig,
    EmailSimulation,
    EmailValidationRow,
    Evidence,
    EvidenceCategory,
    FieldError,
    FilterRule,
    LayerConfig,
    LayerName,
    LayerOutcome,
    MailAddress,
    MetaInfo,
    ParsedEmail,
    ParsedLink,
    ProblemDetail,
    QuizKind,
    QuizOption,
    QuizQuestion,
    Recommendation,
    RiskBand,
    RuleMatch,
    SegmentationConfig,
    SimulationResult,
    SimulationSettings,
    TrainingLevel,
    UserTrainingConfig,
    ValidationReport,
    Verdict,
    default_assumptions,
)

WEIGHTS_HASH = "0000000000000000"
MOCK_DIR = Path(__file__).resolve().parents[2] / "contracts" / "mocks"


def untrained_config() -> LayerConfig:
    return LayerConfig(
        name="Untrained users (v1)",
        org_domains=["contoso.example"],
        email_filter=EmailFilterConfig(
            base_catch_rate=0.35,
            rules=[
                FilterRule(
                    id="quarantine_dmarc_fail",
                    description="Quarantine messages that fail DMARC",
                    match=RuleMatch(feature="auth.dmarc", op="eq", value="fail"),
                    catch_rate=0.85,
                ),
                FilterRule(
                    id="block_executables",
                    description="Block executable and script attachments",
                    match=RuleMatch(
                        feature="attachment.risk_class",
                        op="in",
                        value=["executable", "script"],
                    ),
                    catch_rate=0.98,
                ),
            ],
        ),
        user_training=UserTrainingConfig(level=TrainingLevel.none),
        application_control=ApplicationControlConfig(
            effectiveness=0.25,
            overrides={
                AttachmentRiskClass.macro_document: 0.90,
                AttachmentRiskClass.executable: 0.95,
            },
        ),
        antivirus=AntivirusConfig(detection_rate=0.55),
        segmentation=SegmentationConfig(containment_rate=0.40),
        simulation=SimulationSettings(runs=10_000, seed=42),
    )


def trained_config() -> LayerConfig:
    config = untrained_config()
    return config.model_copy(
        update={
            "name": "Trained users (v2)",
            "user_training": UserTrainingConfig(level=TrainingLevel.advanced),
        }
    )


def _sender() -> MailAddress:
    return MailAddress(
        display_name="Microsoft Account Team",
        address="security@microsoft.com",
        domain="microsoft.com",
        registrable_domain="microsoft.com",
    )


def sample_analysis() -> EmailAnalysis:
    return EmailAnalysis(
        email_id="email_01",
        risk_score=0.96,
        label=Verdict.phishing,
        band=RiskBand.critical,
        attack_vector=AttackVector.credential_harvest,
        vector_reason="The message asks the recipient to sign in and the link imitates Microsoft.",
        evidence=[
            Evidence(
                rule_id="H01",
                category=EvidenceCategory.header,
                title="Reply-To mismatch",
                detail="Replies go to ms-account-verify.com, not microsoft.com.",
                location="Reply-To",
                contribution=1.5,
                user_visible=False,
            ),
            Evidence(
                rule_id="A03",
                category=EvidenceCategory.auth,
                title="DMARC failed",
                detail="microsoft.com did not authenticate this message.",
                location="Authentication-Results",
                contribution=2.0,
                user_visible=False,
            ),
            Evidence(
                rule_id="L02",
                category=EvidenceCategory.domain,
                title="Look-alike domain",
                detail="micros0ft-login.com imitates microsoft.com (homoglyph, 0.98).",
                location="link #1 href",
                contribution=2.45,
                user_visible=True,
            ),
        ],
        advice=[
            "Replies would go to ms-account-verify.com, not microsoft.com. "
            "Don't reply; contact the sender through a channel you already know.",
            "The link goes to micros0ft-login.com, which imitates microsoft.com. "
            "Don't click it. Type microsoft.com into your browser instead.",
            "Report it with the Report Phish button, then delete it.",
        ],
        cue_score=0.72,
        features={
            "auth.dmarc": "fail",
            "header.reply_to_mismatch": True,
            "links.max_lookalike_score": 0.98,
            "content.credential_request": True,
        },
        engine_version=ENGINE_VERSION,
        weights_hash=WEIGHTS_HASH,
    )


def sample_parsed_email() -> ParsedEmail:
    return ParsedEmail(
        message_id="<01@mail.example>",
        sender=_sender(),
        reply_to=[
            MailAddress(
                display_name="",
                address="support@ms-account-verify.com",
                domain="ms-account-verify.com",
                registrable_domain="ms-account-verify.com",
            )
        ],
        return_path=MailAddress(
            address="bounce@ms-account-verify.com",
            domain="ms-account-verify.com",
            registrable_domain="ms-account-verify.com",
        ),
        to=[
            MailAddress(
                display_name="Alex Rivera",
                address="alex.rivera@contoso.example",
                domain="contoso.example",
                registrable_domain="contoso.example",
            )
        ],
        subject="Action required: verify your account",
        date=datetime(2026, 11, 14, 10, 24, tzinfo=UTC),
        auth=AuthResults(
            spf=AuthStatus.FAIL,
            dkim=AuthStatus.FAIL,
            dmarc=AuthStatus.FAIL,
            header_from="microsoft.com",
            smtp_mailfrom="ms-account-verify.com",
        ),
        links=[
            ParsedLink(
                text="https://microsoft.com/verify",
                href="http://micros0ft-login.com/verify",
                source="html",
            )
        ],
        attachments=[],
        body_text=(
            "Dear user, your account will be locked in 24 hours. "
            "Verify at https://microsoft.com/verify."
        ),
        body_text_sanitized=(
            "Dear user, your account will be locked in 24 hours. "
            "Verify at hxxp://micros0ft-login[.]com/verify."
        ),
        parse_warnings=[],
    )


def _funnel(user_stop: float) -> list[LayerOutcome]:
    """Exact illustrative funnel for the untrained (0.30) and trained (0.75) user layer.

    Untrained remaining: 6500, 4550, 3413, 1536, 921.
    Trained user stop is 0.75 of 6500 = 4875, remaining 1625. Later layers keep
    their rates, so the counts below are rounded from that product and are
    examples, not a second golden test.
    """
    if user_stop == 0.30:
        rows = [
            (LayerName.email_filter, 0.35, 10_000, 3_500, "Base catch rate 0.35."),
            (LayerName.user, 0.30, 6_500, 1_950, "Training level none, base catch rate 0.30."),
            (LayerName.application_control, 0.25, 4_550, 1_137, "Effectiveness 0.25."),
            (LayerName.antivirus, 0.55, 3_413, 1_877, "Detection rate 0.55."),
            (LayerName.segmentation, 0.40, 1_536, 615, "Containment rate 0.40."),
        ]
    else:
        rows = [
            (LayerName.email_filter, 0.35, 10_000, 3_500, "Base catch rate 0.35."),
            (LayerName.user, 0.75, 6_500, 4_875, "Training level advanced, base catch rate 0.75."),
            (LayerName.application_control, 0.25, 1_625, 406, "Effectiveness 0.25."),
            (LayerName.antivirus, 0.55, 1_219, 670, "Detection rate 0.55."),
            (LayerName.segmentation, 0.40, 549, 220, "Containment rate 0.40."),
        ]
    return [
        LayerOutcome(
            layer=layer,
            applicable=True,
            p_stop=p_stop,
            reasons=[reason],
            entered=entered,
            stopped=stopped,
        )
        for layer, p_stop, entered, stopped, reason in rows
    ]


def sample_email_simulation(user_stop: float = 0.30) -> EmailSimulation:
    layers = _funnel(user_stop)
    passed = layers[-1].entered - layers[-1].stopped
    runs = 10_000
    closed = 0.0921375 if user_stop == 0.30 else 0.03290625
    return EmailSimulation(
        email_id="email_01",
        attack_vector=AttackVector.malware_attachment,
        layers=layers,
        passed=passed,
        pass_rate=passed / runs,
        ci95=(0.0866, 0.0980) if user_stop == 0.30 else (0.0295, 0.0366),
        closed_form=round(closed, 6),
    )


def _aggregate(sim: EmailSimulation, closed: float) -> AggregateSimulation:
    return AggregateSimulation(
        email_count=1,
        runs=10_000,
        pass_rate=sim.pass_rate,
        blocked_rate=round(1 - sim.pass_rate, 4),
        ci95=sim.ci95,
        closed_form=closed,
        layers=[
            AggregateLayer(
                layer=layer.layer,
                entered=layer.entered,
                stopped=layer.stopped,
                applicable_emails=1,
            )
            for layer in sim.layers
        ],
    )


def sample_simulation(trained: bool = False) -> SimulationResult:
    user_stop = 0.75 if trained else 0.30
    sim = sample_email_simulation(user_stop)
    closed = 0.032906 if trained else 0.092138
    return SimulationResult(
        config_snapshot=trained_config() if trained else untrained_config(),
        runs=10_000,
        seed=42,
        per_email=[sim],
        aggregate=_aggregate(sim, closed),
        engine_version=ENGINE_VERSION,
    )


def sample_comparison() -> ComparisonResult:
    before = sample_simulation(trained=False)
    after = sample_simulation(trained=True)
    return ComparisonResult(
        config_a_name=before.config_snapshot.name,
        config_b_name=after.config_snapshot.name,
        result_a=before,
        result_b=after,
        absolute_reduction=0.0592,
        relative_reduction=0.643,
        narrative=(
            "Improving user training from none to advanced, with all other controls "
            "unchanged, reduces the modeled chance an attack passes every layer "
            "from 9.21% to 3.29%, a 64.3% reduction."
        ),
        changes=[
            ConfigChange(path="user_training.level", before="none", after="advanced"),
        ],
        per_email=[
            EmailComparison(
                email_id="email_01",
                pass_rate_a=before.aggregate.pass_rate,
                pass_rate_b=after.aggregate.pass_rate,
                absolute_reduction=round(before.aggregate.pass_rate - after.aggregate.pass_rate, 4),
            )
        ],
    )


def sample_validation() -> ValidationReport:
    return ValidationReport(
        total=20,
        actual_phishing=12,
        actual_genuine=8,
        correct=18,
        accuracy=0.9,
        precision=0.9167,
        recall=0.9167,
        f1=0.9167,
        false_positive_rate=0.125,
        false_negative_rate=0.0833,
        confusion=ConfusionMatrix(
            true_phishing_pred_phishing=11,
            true_phishing_pred_genuine=1,
            true_genuine_pred_phishing=1,
            true_genuine_pred_genuine=7,
        ),
        rows=[
            EmailValidationRow(
                email_id="email_01",
                filename="01-reply-to-mismatch.eml",
                actual=Verdict.phishing,
                predicted=Verdict.phishing,
                risk_score=0.96,
                correct=True,
                top_evidence="DMARC failed",
            )
        ],
        engine_version=ENGINE_VERSION,
        weights_hash=WEIGHTS_HASH,
    )


def payloads() -> dict[str, BaseModel]:
    return {
        "evidence": sample_analysis().evidence[0],
        "email-analysis": sample_analysis(),
        "parsed-email": sample_parsed_email(),
        "layer-config": untrained_config(),
        "layer-outcome": sample_email_simulation().layers[0],
        "email-simulation": sample_email_simulation(),
        "simulation-result": sample_simulation(),
        "comparison-result": sample_comparison(),
        "recommendation": Recommendation(
            id="raise_training",
            title="Advance user training",
            detail=(
                "Moving from no training to advanced training is the largest modeled "
                "reduction for this mix, because several emails carry no malware for "
                "antivirus to see."
            ),
            layer=LayerName.user,
            absolute_reduction=0.0592,
            relative_reduction=0.643,
            vectors_helped=[
                AttackVector.credential_harvest,
                AttackVector.payment_fraud,
                AttackVector.malware_attachment,
            ],
        ),
        "validation-report": sample_validation(),
        "quiz-question": QuizQuestion(
            id="q1",
            email_id="email_01",
            kind=QuizKind.most_suspicious,
            prompt="Which part of this email is the strongest warning sign?",
            options=[
                QuizOption(id="a", text="The greeting is generic"),
                QuizOption(id="b", text="The link goes to micros0ft-login.com"),
                QuizOption(id="c", text="The message was sent on a Thursday"),
            ],
            answer_id="b",
            explanation=(
                "The visible link text says microsoft.com, but the address is "
                "micros0ft-login.com. That look-alike domain is the strongest sign."
            ),
        ),
        "dataset-summary": DatasetSummary(
            dataset_id="dev",
            name="Development corpus",
            email_count=36,
            phishing_count=None,
            genuine_count=None,
            accuracy=None,
            pass_rate_before=None,
            pass_rate_after=None,
            relative_reduction=None,
        ),
        "domain-record": DomainRecord(
            domain="micros0ft-login.com",
            closest_brand="microsoft.com",
            similarity=0.98,
            technique="homoglyph",
            occurrences=1,
            email_ids=["email_01"],
        ),
        "meta": MetaInfo(
            engine_version=ENGINE_VERSION,
            contract_version=CONTRACT_VERSION,
            weights_hash=None,
            assumptions=default_assumptions(),
        ),
        "problem-detail": ProblemDetail(
            type="https://layersight.local/problems/invalid-config",
            title="Configuration could not be read",
            status=422,
            detail="user_training.level must be none, basic, or advanced.",
            errors=[
                FieldError(
                    field="user_training.level",
                    message="Input should be 'none', 'basic', or 'advanced'.",
                )
            ],
        ),
        "assumptions": default_assumptions(),
    }


def write_mocks(directory: Path = MOCK_DIR) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, model in payloads().items():
        text = model.model_dump_json(by_alias=True, indent=2)
        # Keep a trailing newline so the files are normal text.
        (directory / f"{name}.json").write_text(text + "\n", encoding="utf-8")


def read_mocks(directory: Path = MOCK_DIR) -> dict[str, object]:
    loaded: dict[str, object] = {}
    for name in payloads():
        loaded[name] = json.loads((directory / f"{name}.json").read_text(encoding="utf-8"))
    return loaded


if __name__ == "__main__":
    write_mocks()
    print(f"wrote {len(payloads())} mocks to {MOCK_DIR}")
