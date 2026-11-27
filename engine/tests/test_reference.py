"""Reference lists are present, parse, and ship inside the package."""

from __future__ import annotations

from importlib.resources import files

import yaml

REFERENCE = files("layersight") / "reference"


def _text(name: str) -> str:
    return (REFERENCE / name).read_text(encoding="utf-8")


def test_public_suffix_list_is_vendored() -> None:
    listing = _text("public_suffix_list.dat")
    assert "BEGIN ICANN DOMAINS" in listing
    assert "com" in listing.splitlines()
    assert "co.uk" in listing


def test_brands_cover_the_domains_the_corpus_imitates() -> None:
    document = yaml.safe_load(_text("brands.yaml"))
    domains = {domain for brand in document["brands"] for domain in brand["domains"]}
    for expected in ("microsoft.com", "paypal.com", "amazon.com", "dhl.com", "github.com"):
        assert expected in domains


def _names(filename: str) -> set[str]:
    return {
        line.strip() for line in _text(filename).splitlines() if line and not line.startswith("#")
    }


def test_freemail_and_shorteners_are_line_lists() -> None:
    freemail = _names("freemail.txt")
    shorteners = _names("shorteners.txt")
    assert "gmail.com" in freemail
    assert "bit.ly" in shorteners


def test_homoglyph_map_has_the_worked_substitutions() -> None:
    document = yaml.safe_load(_text("homoglyphs.yaml"))
    singles = document.get("single") or document.get("characters") or document.get("chars") or {}
    assert singles["0"] == "o"
    assert singles["1"] == "l"
    pairs = document.get("multi") or []
    sequences = document.get("sequences") or []
    has_rn = ["rn", "m"] in pairs or any(
        item.get("from") == "rn" and item.get("to") == "m" for item in sequences
    )
    assert has_rn


def test_suspicious_tlds_include_the_corpus_examples() -> None:
    document = yaml.safe_load(_text("tlds.yaml"))
    assert "tk" in document["suspicious"]
    assert "zip" in document["suspicious"]
