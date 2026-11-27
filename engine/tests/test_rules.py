"""Each rule has a positive and a negative case. Labels are not inputs."""

from __future__ import annotations

from layersight.scoring.analyze import analyze_email

PASS = (
    "mx.test; spf=pass smtp.mailfrom=company.com; "
    "dkim=pass header.d=company.com; dmarc=pass header.from=company.com"
)
FAIL = (
    "mx.test; spf=fail smtp.mailfrom=login-alert.net; "
    "dkim=fail header.d=login-alert.net; dmarc=fail header.from=login-alert.net"
)


def mail(
    *,
    sender: str = "IT <it@company.com>",
    subject: str = "Notes",
    body: str = "Hello Ada,\n\nThe notes are in the folder.\n",
    reply: str | None = None,
    return_path: str | None = None,
    auth: str | None = PASS,
    html: bool = False,
) -> str:
    content_type = "text/html; charset=utf-8" if html else "text/plain; charset=utf-8"
    lines = [
        f"From: {sender}",
        "To: Ada Lopez <ada@company.com>",
        f"Subject: {subject}",
        "Date: Tue, 24 Nov 2026 10:00:00 +0000",
        "MIME-Version: 1.0",
        f"Content-Type: {content_type}",
    ]
    if reply:
        lines.append(f"Reply-To: {reply}")
    if return_path:
        lines.append(f"Return-Path: <{return_path}>")
    if auth:
        lines.append(f"Authentication-Results: {auth}")
    return "\n".join(lines) + "\n\n" + body


def fired(raw: str) -> set[str]:
    return {item.rule_id for item in analyze_email(raw).analysis.evidence}


def test_header_rules() -> None:
    assert "H01" in fired(mail(reply="Other <a@other-domain.test>"))
    assert "H01" not in fired(mail(reply="IT <it@company.com>"))
    assert "H02" in fired(mail(sender="PayPal <service@paypa1.com>", auth=FAIL))
    assert "H02" not in fired(mail(sender="IT Helpdesk <it@company.com>"))
    assert "H03" in fired(mail(return_path="bounce@other-domain.test"))
    assert "H03" not in fired(mail(return_path="bounce@company.com"))
    assert "H04" in fired(mail(sender='"Alex Morgan, CEO" <alex.morgan@gmail.com>', auth=None))
    assert "H04" not in fired(mail(sender="Ada Lopez <ada@gmail.com>", auth=None))


def test_auth_rules() -> None:
    assert "A01" in fired(mail(auth=FAIL))
    soft = (
        "mx.test; spf=softfail smtp.mailfrom=company.com; "
        "dkim=pass header.d=company.com; dmarc=pass header.from=company.com"
    )
    assert "A01" in fired(mail(auth=soft))
    assert "A01" not in fired(mail(auth=PASS))
    assert "A02" in fired(mail(auth=None))
    assert "A02" not in fired(mail(auth=PASS))
    assert "A03" in fired(mail(auth=FAIL))
    assert "A03" not in fired(mail(auth=PASS))
    assert "A04" in fired(mail(auth=PASS))
    assert "A04" not in fired(mail(auth=FAIL))


def test_link_rules() -> None:
    hidden = mail(
        auth=FAIL,
        html=True,
        body='<p>Verify your account.</p><p><a href="http://micros0ft.com/login">https://microsoft.com/login</a></p>',
    )
    ids = fired(hidden)
    assert "L01" in ids
    assert "L02" in ids
    assert "L08" in ids
    plain = mail(body="Hello Ada,\n\nhttps://harbor-letter.com/story\n", sender="News <news@harbor-letter.com>")
    assert "L02" not in fired(plain)
    assert "L03" in fired(mail(auth=FAIL, body="Verify your account.\n\nhttp://203.0.113.10/login\n"))
    puny = "p\u0430ypal.com".encode("idna").decode("ascii")
    assert "L04" in fired(mail(auth=FAIL, body=f"Verify your account.\n\nhttps://{puny}/signin\n"))
    assert "L05" in fired(mail(body="Notes.\n\nhttps://bit.ly/harbor-brief\n"))
    path = mail(
        auth=FAIL,
        html=True,
        body='<p>Verify your account.</p><p><a href="https://evil-example.com/paypal/login">Sign in</a></p>',
    )
    assert "L06" in fired(path)
    assert "L07" in fired(mail(auth=FAIL, body="Verify your account.\n\nhttps://account-check.tk/login\n"))
    assert "L09" in fired(mail(body="Hello.\n\nhttps://bit.ly/harbor-brief\n", sender="News <news@harbor-letter.com>"))
    assert "L09" not in fired(mail(body="Hello.\n\nhttps://company.com/notes\n"))


def test_content_and_attachment_rules() -> None:
    assert "C01" in fired(mail(body="Hello Ada,\n\nPlease reply immediately.\n"))
    assert "C01" not in fired(mail())
    assert "C02" in fired(mail(body="Please verify your account.\n"))
    assert "C02" not in fired(mail(body="Ada, reset your password on the intranet when you can.\n"))
    assert "C03" in fired(mail(body="Please wire the payment to the new bank details.\n"))
    assert "C04" in fired(mail(body="Dear user,\n\nThe notes are attached in spirit only.\n"))
    assert "C05" in fired(mail(body="Your mailbox will be suspended tonight.\n"))
    assert "T01" in fired(mail(body="File.\n\nAttachment: update.exe (application/x-msdownload)\n"))
    assert "T02" in fired(mail(body="File.\n\nAttachment: invoice.pdf.exe (application/x-msdownload)\n"))
    assert "T03" in fired(mail(body="File.\n\nAttachment: budget.xlsm (application/octet-stream)\n"))
    assert "T04" in fired(mail(body="File.\n\nAttachment: docs.zip (application/zip)\n"))
    assert "T05" in fired(mail(body="File.\n\nAttachment: page.html (text/html)\n"))
    assert "T01" not in fired(mail(body="File.\n\nAttachment: invoice.pdf (application/pdf)\n"))


def test_trust_rules() -> None:
    trusted = fired(mail(body="Hello Ada,\n\nhttps://company.com/notes\n"))
    assert "G01" in trusted
    assert "G02" in trusted
    assert "G01" not in fired(mail(auth=FAIL, body="Verify your account.\n"))
    assert "G02" not in fired(mail(body="Hello.\n\nhttps://bit.ly/x\n"))


def test_classifier_ignores_filename_and_label() -> None:
    bundle = analyze_email(mail(subject="harmless-genuine.eml", body="Please verify your account within 24 hours."))
    assert bundle.analysis.label == "phishing"
    assert "genuine" not in bundle.analysis.features
