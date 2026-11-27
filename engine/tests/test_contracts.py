"""The models the rest of the product shares can be built and read back."""

from __future__ import annotations

from layersight import __version__
from layersight.models import EmailAnalysis, Evidence, ParsedEmail


def test_analysis_round_trip() -> None:
    analysis = EmailAnalysis(
        email_id="email_01",
        risk_score=0.96,
        label="phishing",
        band="critical",
        attack_vector="credential_harvest",
        vector_reason="The link imitates a brand the recipient trusts.",
        evidence=[
            Evidence(
                rule_id="L02",
                category="domain",
                title="Look-alike domain",
                detail="micros0ft-login.com imitates microsoft.com.",
                location="link #1",
                contribution=2.45,
                share=0.4,
                user_visible=True,
            )
        ],
        advice=["Don't click the link. Type the real site into the browser."],
        cue_score=0.72,
        features={"links.max_lookalike_score": 0.98},
        engine_version=__version__,
        weights_hash="0" * 16,
    )
    restored = EmailAnalysis.model_validate_json(analysis.model_dump_json())
    assert restored == analysis


def test_parsed_email_accepts_an_empty_message() -> None:
    parsed = ParsedEmail()
    assert parsed.auth.spf == "none"
    assert parsed.attachments == []
