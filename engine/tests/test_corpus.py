"""The development corpus is labeled, covers every rule, and is not the official set."""

from __future__ import annotations

import csv
from pathlib import Path

import yaml

from layersight.config.schema import LayerConfig

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "data" / "dev"
TEST = ROOT / "data" / "test"

RULES = {
    "H01",
    "H02",
    "H03",
    "H04",
    "A01",
    "A02",
    "A03",
    "A04",
    "L01",
    "L02",
    "L03",
    "L04",
    "L05",
    "L06",
    "L07",
    "L08",
    "L09",
    "C01",
    "C02",
    "C03",
    "C04",
    "C05",
    "T01",
    "T02",
    "T03",
    "T04",
    "T05",
    "G01",
    "G02",
}


def _labels() -> dict[str, str]:
    with (DEV / "labels.csv").open(encoding="utf-8", newline="") as handle:
        return {row["filename"]: row["label"] for row in csv.DictReader(handle)}


def test_at_least_thirty_labeled_emails() -> None:
    labels = _labels()
    assert len(labels) >= 30
    assert set(labels.values()) == {"phishing", "genuine"}
    on_disk = {path.name for path in (DEV / "emails").glob("*.eml")}
    assert on_disk == set(labels)


def test_every_rule_has_a_real_email() -> None:
    labels = _labels()
    coverage = yaml.safe_load((DEV / "coverage.yaml").read_text(encoding="utf-8"))
    assert set(coverage["rules"]) == RULES
    for rule, filenames in coverage["rules"].items():
        assert filenames, rule
        for filename in filenames:
            assert filename in labels, filename
            assert (DEV / "emails" / filename).is_file()


def test_hard_cases_have_the_right_label() -> None:
    labels = _labels()
    coverage = yaml.safe_load((DEV / "coverage.yaml").read_text(encoding="utf-8"))
    positives = coverage["hard_positives"]
    negatives = coverage["hard_negatives"]
    assert len(positives) >= 3
    assert len(negatives) >= 5
    assert {labels[name] for name in positives} == {"phishing"}
    assert {labels[name] for name in negatives} == {"genuine"}


def test_configs_are_valid_and_differ_only_by_training() -> None:
    untrained = yaml.safe_load((DEV / "configs" / "untrained.yaml").read_text(encoding="utf-8"))
    trained = yaml.safe_load((DEV / "configs" / "trained.yaml").read_text(encoding="utf-8"))
    LayerConfig.model_validate(untrained)
    LayerConfig.model_validate(trained)
    assert untrained["user_training"]["level"] == "none"
    assert trained["user_training"]["level"] == "advanced"
    untrained["name"] = trained["name"]
    untrained["user_training"]["level"] = trained["user_training"]["level"]
    assert untrained == trained


def test_practice_test_set_is_labeled_and_not_claimed_official() -> None:
    """A local 20-email set stands in until the hackathon files arrive."""
    emails = sorted(path.name for path in (TEST / "emails").glob("*.eml"))
    with (TEST / "labels.csv").open(encoding="utf-8", newline="") as handle:
        labels = {row["filename"]: row["label"].strip() for row in csv.DictReader(handle)}
    assert len(emails) == 20
    assert set(labels) == set(emails)
    assert sum(label == "phishing" for label in labels.values()) == 12
    assert sum(label == "genuine" for label in labels.values()) == 8
    for name in ("untrained.yaml", "trained.yaml"):
        LayerConfig.model_validate(
            yaml.safe_load((TEST / "configs" / name).read_text(encoding="utf-8"))
        )
    readme = (TEST / "README.md").read_text(encoding="utf-8")
    assert "not the official" in readme.lower() or "has not been delivered" in readme.lower()
