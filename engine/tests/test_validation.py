from pathlib import Path

import pytest

from layersight.scoring.analyze import analyze_email
from layersight.validation.metrics import validate_directory

ROOT = Path(__file__).resolve().parents[2]
RULES = {
    "H01", "H02", "H03", "H04",
    "A01", "A02", "A03", "A04",
    "L01", "L02", "L03", "L04", "L05", "L06", "L07", "L08", "L09",
    "C01", "C02", "C03", "C04", "C05",
    "T01", "T02", "T03", "T04", "T05",
    "G01", "G02",
}


@pytest.mark.validation
def test_test_set_meets_the_gate() -> None:
    report = validate_directory(ROOT / "data" / "test" / "emails", ROOT / "data" / "test" / "labels.csv")
    assert report.total == 20
    assert report.actual_phishing == 12
    assert report.actual_genuine == 8
    assert report.accuracy is not None
    assert report.accuracy >= 0.90
    assert report.correct is not None and report.correct >= 18


def test_dev_set_exercises_every_rule() -> None:
    directory = ROOT / "data" / "dev" / "emails"
    fired: set[str] = set()
    for path in directory.glob("*.eml"):
        bundle = analyze_email(path.read_text(encoding="utf-8"))
        fired.update(item.rule_id for item in bundle.analysis.evidence)
    assert RULES <= fired


def test_compromised_mailbox_is_explained() -> None:
    raw = (ROOT / "data" / "test" / "emails" / "12-compromised-mailbox.eml").read_text(encoding="utf-8")
    evidence = {item.rule_id for item in analyze_email(raw).analysis.evidence}
    assert {"A04", "C02", "G01", "G02"} <= evidence
