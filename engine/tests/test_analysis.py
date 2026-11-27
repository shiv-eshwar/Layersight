"""Parser, look-alike scoring, and the development-set accuracy gate."""

from __future__ import annotations

from pathlib import Path

import yaml

from layersight.features.domains import similarity
from layersight.parsing.eml import parse_email
from layersight.refs import protected_domains
from layersight.scoring.analyze import analyze_email
from layersight.validation.metrics import validate_directory

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "data" / "dev"
ORG = ["company.com"]


def test_parser_survives_a_broken_message() -> None:
    parsed = parse_email("this is not an email\x00")
    assert parsed.parse_warnings
    assert parsed.subject == ""


def test_parser_inserts_the_missing_header_gap() -> None:
    raw = "From: Ada <ada@company.com>\nSubject: Hello\nHello Ada.\n"
    parsed = parse_email(raw)
    assert parsed.sender.address == "ada@company.com"
    assert parsed.subject == "Hello"
    assert "Hello Ada." in parsed.body_text


def test_similarity_names_each_technique() -> None:
    protected = protected_domains(["company.com"])
    cases = {
        "micros0ft.com": "homoglyph",
        "microsoft.co": "tld_swap",
        "paypal.com.secure-login.io": "subdomain_abuse",
        "amazon-support.net": "combosquat",
        "amazom.com": "typosquat",
        "microsoft.com": "legitimate",
    }
    for host, technique in cases.items():
        hit = similarity(host, protected)
        assert hit.technique == technique, host
        assert hit.diff or technique == "legitimate"


def test_every_rule_fires_and_also_stays_silent() -> None:
    coverage = yaml.safe_load((DEV / "coverage.yaml").read_text(encoding="utf-8"))
    rules = set(coverage["rules"])
    fired: set[str] = set()
    silent: set[str] = set()
    for path in sorted((DEV / "emails").glob("*.eml")):
        evidence = {item.rule_id for item in analyze_email(path.read_text(encoding="utf-8"), ORG).analysis.evidence}
        fired |= evidence
        silent |= rules - evidence
    assert rules <= fired
    assert rules <= silent


def test_evidence_explains_itself() -> None:
    for path in sorted((DEV / "emails").glob("*.eml")):
        analysis = analyze_email(path.read_text(encoding="utf-8"), ORG).analysis
        assert analysis.advice
        for item in analysis.evidence:
            assert item.detail.strip()
            assert item.title.strip()


def test_dev_corpus_meets_the_accuracy_gate() -> None:
    report = validate_directory(DEV / "emails", DEV / "labels.csv", ORG)
    assert report.labeled >= 30
    assert report.accuracy is not None
    assert report.accuracy >= 0.90
