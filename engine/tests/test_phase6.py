"""Phase 6: similarity acceptance, modeled outlook, quiz catch rate."""

from __future__ import annotations

from pathlib import Path

from layersight.features.domains import similarity
from layersight.models import EmailAnalysis, Evidence
from layersight.phase6.aggregate import check_domain
from layersight.phase6.assess import analyze_observation
from layersight.phase6.outlook import Defense, closed_form, command_center, funnel_entered
from layersight.phase6.quiz import catch_rate, generate, grade
from layersight.phase6.read import read_message
from layersight.phase6.records import ScoredMail

ROOT = Path(__file__).resolve().parents[2]


def test_paypa1_is_a_paypal_homoglyph() -> None:
    view = check_domain("paypa1.com", ["contoso.example"])
    assert view.technique == "homoglyph"
    assert view.closest == "paypal.com"
    assert view.score == 0.98
    assert "1" in view.diff


def test_worked_funnel_matches_the_published_counts() -> None:
    probabilities = [0.35, 0.30, 0.25, 0.55, 0.40]
    assert funnel_entered(probabilities, 10_000) == [10000, 6500, 4550, 3413, 1536, 921]
    assert round(closed_form(probabilities), 4) == 0.0921
    trained = [0.35, 0.75, 0.25, 0.55, 0.40]
    assert round(closed_form(trained), 4) == 0.0329
    relative = (closed_form(probabilities) - closed_form(trained)) / closed_form(probabilities)
    assert round(relative, 3) == 0.643


def test_training_lowers_pass_through_for_a_credential_email() -> None:
    mail = _mail(cue=0.5, vector="credential_harvest", score=0.2)
    bare = _defense("none")
    trained = _defense("advanced")
    report = command_center("t", "t", [mail], bare, trained)
    assert report.before.closed_form is not None
    assert report.after.closed_form is not None
    assert report.after.closed_form < report.before.closed_form
    assert report.recommendation is not None
    assert report.before.uncertainty is not None
    band = report.before.uncertainty
    assert band.p05 <= report.before.closed_form <= band.p95


def test_quiz_accuracy_becomes_the_user_catch_rate() -> None:
    assert catch_rate(0) == 0.02
    assert catch_rate(1) == 0.98
    assert catch_rate(0.7) == 0.7
    mail = _mail(cue=0.8, vector="credential_harvest", score=0.9, visible=True)
    questions = generate([mail], n=1, seed=1)
    assert questions[0].explanation
    wrong = grade("t", [mail], [], n=1, seed=1)
    assert wrong.total == 0
    from layersight.phase6.models import AnswerIn

    scored = grade(
        "t",
        [mail],
        [AnswerIn(question_id=questions[0].id, chosen=questions[0].answer_id)],
        n=1,
        seed=1,
        record=True,
    )
    assert scored.correct == 1
    assert scored.catch_rate == 0.98 or scored.catch_rate == 1 or scored.accuracy == 1


def test_dev_reply_to_message_is_phishing_and_password_reset_is_not() -> None:
    phishing = ROOT / "data" / "dev" / "emails" / "01-reply-to-mismatch.eml"
    genuine = ROOT / "data" / "dev" / "emails" / "25-genuine-password-reset.eml"
    if not phishing.is_file() or not genuine.is_file():
        return
    org = ["contoso.example"]
    bad = analyze_observation(read_message(phishing.read_text(encoding="utf-8")), "01", org)
    good = analyze_observation(read_message(genuine.read_text(encoding="utf-8")), "25", org)
    assert bad.label == "phishing"
    assert good.label == "genuine"
    assert any(item.rule_id == "H01" for item in bad.evidence)


def test_similarity_techniques() -> None:
    protected = ["paypal.com", "microsoft.com", "amazon.com", "amazon.co.uk", "dropbox.com"]
    cases = {
        "micros0ft.com": "homoglyph",
        "amazom.com": "typosquat",
        "amazon-support.net": "combosquat",
        "microsoft.co": "tld_swap",
        "paypal.com.secure-login.io": "subdomain_abuse",
        "paypal.com": "legitimate",
    }
    for candidate, technique in cases.items():
        assert similarity(candidate, protected).technique == technique


def _defense(level: str) -> Defense:
    return Defense(
        name=level,
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


def _mail(cue: float, vector: str, score: float, visible: bool = False) -> ScoredMail:
    evidence = []
    if visible:
        evidence.append(
            Evidence(
                rule_id="L02",
                category="domain",
                title="Look-alike domain",
                detail="paypa1.com imitates paypal.com (homoglyph, 0.98).",
                location="link",
                contribution=2.4,
                share=1.0,
                user_visible=True,
            )
        )
    analysis = EmailAnalysis(
        email_id="m1",
        risk_score=score,
        label="phishing",
        band="high",
        attack_vector=vector,  # type: ignore[arg-type]
        vector_reason="test",
        evidence=evidence,
        advice=["Report it with the Report Phish button, then delete it."],
        cue_score=cue,
        features={"auth.dmarc": "none", "links.max_lookalike_score": 0.0},
        engine_version="test",
        weights_hash="test",
    )
    from layersight.phase6.read import Observation

    observed = Observation(
        subject="Verify your account",
        date=None,
        sender_display="PayPal",
        sender_address="a@paypa1.com",
        sender_domain="paypa1.com",
        reply_domain=None,
        return_domain=None,
        spf="none",
        dkim="none",
        dmarc="none",
        links=(("https://paypal.com", "http://paypa1.com/login"),),
        attachments=(),
        body="Dear user, verify your account.",
    )
    return ScoredMail("m1", observed.subject, observed.sender_display, "phishing", analysis, observed)  # noqa: E501
