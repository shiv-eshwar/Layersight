from layersight.features.domains import registrable, similarity


def test_registrable_domains() -> None:
    assert registrable("paypal.com.secure-login.io") == "secure-login.io"
    assert registrable("login.microsoft.co.uk") == "microsoft.co.uk"
    assert registrable("micros0ft.com") == "micros0ft.com"


def test_similarity_techniques() -> None:
    protected = ("microsoft.com", "paypal.com", "amazon.com", "company.com")
    assert similarity("microsoft.com", protected).technique == "legitimate"
    homo = similarity("micros0ft.com", protected)
    assert homo.technique == "homoglyph"
    assert homo.score == 0.98
    assert homo.closest == "microsoft.com"
    assert any(item.changed for item in homo.diff)
    assert similarity("microsoft.co", protected).technique == "tld_swap"
    assert similarity("paypal.com.secure-login.io", protected).technique == "subdomain_abuse"
    assert similarity("amazon-support.net", protected).technique == "combosquat"
    typo = similarity("amazom.com", protected)
    assert typo.technique == "typosquat"
    assert typo.score >= 0.80
    assert similarity("harbor-letter.com", protected).score < 0.80
