"""Write the stand-in test set and the dev set. Labels are not visible to the classifier."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUNY = "p\u0430ypal.com".encode("idna").decode("ascii")

PASS = "mx.example.net; spf=pass smtp.mailfrom={d}; dkim=pass header.d={d}; dmarc=pass header.from={d}"
FAIL = "mx.example.net; spf=fail smtp.mailfrom={d}; dkim=fail header.d={d}; dmarc=fail header.from={d}"
SOFT = "mx.example.net; spf=softfail smtp.mailfrom={d}; dkim=pass header.d={d}; dmarc=pass header.from={d}"


def auth(kind: str | None, domain: str) -> str | None:
    if kind is None:
        return None
    template = {"pass": PASS, "fail": FAIL, "softfail": SOFT}[kind]
    return template.format(d=domain)


def render(
    *,
    subject: str,
    sender: str,
    body: str,
    reply: str | None = None,
    return_path: str | None = None,
    auth_header: str | None = None,
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
    if auth_header:
        lines.append(f"Authentication-Results: {auth_header}")
    return "\n".join(lines) + "\n\n" + body.strip() + "\n"


def html_link(paragraphs: str, href: str, text: str) -> str:
    return f"<html><body><p>{paragraphs}</p><p><a href=\"{href}\">{text}</a></p></body></html>"


def write_split(split: str, rows: list[tuple[str, str, str]]) -> None:
    directory = ROOT / "data" / split / "emails"
    directory.mkdir(parents=True, exist_ok=True)
    for path in directory.glob("*"):
        if path.suffix in {".eml", ".txt"}:
            path.unlink()
    labels = ROOT / "data" / split / "labels.csv"
    with labels.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["filename", "label"])
        for filename, label, raw in rows:
            (directory / filename).write_text(raw, encoding="utf-8")
            writer.writerow([filename, label])


def test_rows() -> list[tuple[str, str, str]]:
    return [
        (
            "01-reply-mismatch.eml",
            "phishing",
            render(
                subject="Your mailbox will be suspended",
                sender="Microsoft Account Team <security@microsoft.com>",
                reply="Support <support@ms-account-verify.com>",
                return_path="bounce@ms-account-verify.com",
                auth_header=auth("fail", "ms-account-verify.com"),
                html=True,
                body=html_link(
                    "Dear user, verify your account within 24 hours or it will be suspended.",
                    "http://micros0ft.com/login",
                    "https://microsoft.com/login",
                ),
            ),
        ),
        (
            "02-freemail-ceo.eml",
            "phishing",
            render(
                subject="Need this sent today",
                sender='"Alex Morgan, CEO" <alex.morgan@gmail.com>',
                body="Please wire the payment to the new bank details immediately. Do not call me.",
            ),
        ),
        (
            "03-paypal-homoglyph.eml",
            "phishing",
            render(
                subject="PayPal receipt problem",
                sender="PayPal Service <service@paypa1.com>",
                auth_header=auth("fail", "paypa1.com"),
                html=True,
                body=html_link(
                    "Dear customer, verify your account within 24 hours.",
                    "https://paypa1.com/signin",
                    "https://paypal.com/signin",
                ),
            ),
        ),
        (
            "04-subdomain.eml",
            "phishing",
            render(
                subject="PayPal sign-in",
                sender="PayPal Security <noreply@secure-login.io>",
                auth_header=auth("fail", "secure-login.io"),
                html=True,
                body=html_link(
                    "Verify your account.",
                    "http://paypal.com.secure-login.io/signin",
                    "https://www.paypal.com/signin",
                ),
            ),
        ),
        (
            "05-executable.eml",
            "phishing",
            render(
                subject="Invoice attached",
                sender="Billing <billing@northwind-supply.com>",
                body="Open the invoice immediately.\n\nAttachment: invoice.pdf.exe (application/x-msdownload)\n",
            ),
        ),
        (
            "06-macro.eml",
            "phishing",
            render(
                subject="Payroll file",
                sender="Payroll <payroll@people-ops.net>",
                auth_header=auth("fail", "people-ops.net"),
                body=(
                    "Your access will be suspended within 24 hours. Enable the document to review payroll.\n\n"
                    "Attachment: payroll.xlsm (application/vnd.ms-excel.sheet.macroEnabled.12)\n"
                ),
            ),
        ),
        (
            "07-bec.eml",
            "phishing",
            render(
                subject="Updated payment instructions",
                sender='"Jordan Lee, CFO" <jordan.lee@ledger-mail.com>',
                reply="Jordan Lee <jordan.lee@pay-update.com>",
                auth_header=auth("fail", "ledger-mail.com"),
                body="Please wire the payment to the new bank details immediately.",
            ),
        ),
        (
            "08-shortener.eml",
            "phishing",
            render(
                subject="Portal check",
                sender="Helpdesk <help@desk-notify.com>",
                auth_header=auth("fail", "desk-notify.com"),
                body="Dear user, verify your account.\n\nhttps://bit.ly/acme-login\n",
            ),
        ),
        (
            "09-ip-link.eml",
            "phishing",
            render(
                subject="Company login",
                sender="Security <security@login-alert.net>",
                auth_header=auth("fail", "login-alert.net"),
                html=True,
                body=html_link(
                    "Verify your account within 24 hours.",
                    "http://203.0.113.10/login",
                    "https://company.com/login",
                ),
            ),
        ),
        (
            "10-punycode.eml",
            "phishing",
            render(
                subject="PayPal security check",
                sender=f"PayPal <service@{PUNY}>",
                auth_header=auth("fail", PUNY),
                html=True,
                body=html_link(
                    "Verify your account.",
                    f"https://{PUNY}/signin",
                    "https://paypal.com/signin",
                ),
            ),
        ),
        (
            "11-archive-notice.eml",
            "phishing",
            render(
                subject="Final notice",
                sender="Files Service <files@cloud-share.net>",
                body=(
                    "Dear user, final notice, your access will be suspended. Open the archive.\n\n"
                    "Attachment: files.zip (application/zip)\n"
                ),
            ),
        ),
        (
            "12-compromised-mailbox.eml",
            "phishing",
            render(
                subject="Password confirmation",
                sender="IT Helpdesk <it@company.com>",
                reply="IT Helpdesk <it@company.com>",
                auth_header=auth("pass", "company.com"),
                html=True,
                body=html_link(
                    "Dear user, your account will be suspended within 24 hours. Verify your account and confirm your password.",
                    "https://company.com/password-reset",
                    "https://company.com/password-reset",
                ),
            ),
        ),
        (
            "13-password-reset.eml",
            "genuine",
            render(
                subject="Reset your password",
                sender="IT <it@company.com>",
                auth_header=auth("pass", "company.com"),
                body="Ada, use this page when you want to reset your password.\n\nhttps://company.com/reset\n",
            ),
        ),
        (
            "14-it-notice.eml",
            "genuine",
            render(
                subject="Mail server restart",
                sender="IT <it@company.com>",
                auth_header=auth("pass", "company.com"),
                body="Ada, the mail servers will be restarted this evening. No action is needed.",
            ),
        ),
        (
            "15-newsletter.eml",
            "genuine",
            render(
                subject="Harbor weekly",
                sender="Harbor Weekly <news@harbor-letter.com>",
                auth_header=auth("pass", "harbor-letter.com"),
                body="Dear user, the weekly briefing is ready.\n\nhttps://bit.ly/harbor-brief\n",
            ),
        ),
        (
            "16-invoice-pdf.eml",
            "genuine",
            render(
                subject="March invoice",
                sender="Billing <billing@northwind-supply.com>",
                auth_header=auth("pass", "northwind-supply.com"),
                body="Ada, the March invoice is attached. Please settle it by the 30th.\n\nAttachment: invoice.pdf (application/pdf)\n",
            ),
        ),
        (
            "17-shipping.eml",
            "genuine",
            render(
                subject="Shipment departed",
                sender="Parcel Route <updates@parcel-route.com>",
                auth_header=auth("pass", "parcel-route.com"),
                body="Ada, your shipment left the depot this morning.\n\nhttps://parcel-route.com/track/4491\n",
            ),
        ),
        (
            "18-hr-benefits.eml",
            "genuine",
            render(
                subject="Open enrollment",
                sender="People Team <people@company.com>",
                auth_header=auth("pass", "company.com"),
                body="Ada, open enrollment starts next Monday. The guide is on the intranet.",
            ),
        ),
        (
            "19-meeting-notes.eml",
            "genuine",
            render(
                subject="Monday planning notes",
                sender="Priya Shah <priya.shah@company.com>",
                auth_header=auth("pass", "company.com"),
                body="Ada, notes from Monday's planning meeting are in the shared folder.",
            ),
        ),
        (
            "20-receipt.eml",
            "genuine",
            render(
                subject="Renewal receipt",
                sender="Billing <billing@company.com>",
                auth_header=auth("pass", "company.com"),
                body="Ada, this receipt confirms the software renewal paid on 12 November.",
            ),
        ),
    ]


def strong(body: str, **kwargs: object) -> str:
    sender = str(kwargs.get("sender", "Security <security@login-alert.net>"))
    domain = sender.split("@")[-1].rstrip(">")
    return render(
        subject=str(kwargs.get("subject", "Account notice")),
        sender=sender,
        reply=kwargs.get("reply"),  # type: ignore[arg-type]
        return_path=kwargs.get("return_path"),  # type: ignore[arg-type]
        auth_header=kwargs.get("auth_header", auth("fail", domain)),  # type: ignore[arg-type]
        html=bool(kwargs.get("html", False)),
        body=body,
    )


def dev_rows() -> list[tuple[str, str, str]]:
    phish = "phishing"
    real = "genuine"
    rows: list[tuple[str, str, str]] = [
        ("d01-reply.eml", phish, strong("Verify your account within 24 hours.", sender="Microsoft <security@microsoft.com>", reply="A <a@ms-account-verify.com>", auth_header=auth("fail", "ms-account-verify.com"))),
        ("d02-display.eml", phish, strong("Verify your account.", sender="Amazon Support <alert@random-mail.test>", auth_header=auth("fail", "random-mail.test"))),
        ("d03-return-path.eml", phish, strong("Verify your account.", sender="IT <it@company.com>", return_path="bounce@other-mail.test", auth_header=auth("fail", "other-mail.test"))),
        ("d04-freemail.eml", phish, render(subject="Request", sender='"Sam Rivera, CEO" <sam.rivera@yahoo.com>', body="Please wire the payment immediately.")),
        ("d05-spf.eml", phish, strong("Verify your account within 24 hours.", auth_header=auth("fail", "login-alert.net"))),
        ("d06-dkim.eml", phish, strong("Verify your account within 24 hours.", auth_header="mx.example.net; spf=pass smtp.mailfrom=login-alert.net; dkim=fail header.d=login-alert.net; dmarc=fail header.from=login-alert.net")),
        ("d07-dmarc.eml", phish, strong("Verify your account within 24 hours.", auth_header=auth("fail", "login-alert.net"))),
        ("d08-link-text.eml", phish, strong(html_link("Verify your account within 24 hours.", "http://micros0ft.com/login", "https://microsoft.com/login"), html=True)),
        ("d09-homoglyph.eml", phish, strong("Verify your account.\n\nhttps://micros0ft.com/login\n")),
        ("d10-ip.eml", phish, strong("Verify your account.\n\nhttp://198.51.100.20/login\n")),
        ("d11-puny.eml", phish, strong(f"Verify your account.\n\nhttps://{PUNY}/web\n")),
        ("d12-short.eml", phish, strong("Verify your account.\n\nhttps://tinyurl.com/acct-check\n")),
        ("d13-brand-path.eml", phish, strong(html_link("Verify your account.", "https://evil-example.com/paypal/login", "Sign in"), html=True)),
        ("d14-tld.eml", phish, strong("Verify your account within 24 hours.\n\nhttps://account-check.tk/login\n")),
        ("d15-http.eml", phish, strong("Verify your account.\n\nhttp://login-alert.net/login\n")),
        ("d16-unrelated.eml", phish, strong("Verify your account.\n\nhttps://other-portal.test/enter\n", sender="Notes <notes@harbor-letter.com>", auth_header=auth("fail", "harbor-letter.com"))),
        ("d17-urgency.eml", phish, strong("This is a final notice. Verify your account.")),
        ("d18-credential.eml", phish, strong("Please confirm your password.")),
        ("d19-payment.eml", phish, strong("Wire the payment to the new bank details.", sender='"CFO Office" <cfo@ledger-mail.com>', auth_header=auth("fail", "ledger-mail.com"))),
        ("d20-greeting.eml", phish, strong("Dear customer, verify your account within 24 hours.")),
        ("d21-threat.eml", phish, strong("Your mailbox will be deleted. Verify your account.")),
        ("d22-exe.eml", phish, strong("See the file.\n\nAttachment: update.exe (application/x-msdownload)\n")),
        ("d23-double.eml", phish, strong("See the file.\n\nAttachment: photo.jpg.exe (application/x-msdownload)\n")),
        ("d24-macro.eml", phish, strong("Review the sheet.\n\nAttachment: budget.xlsm (application/vnd.ms-excel.sheet.macroEnabled.12)\n")),
        ("d25-archive.eml", phish, strong("The bundle is attached.\n\nAttachment: docs.zip (application/zip)\nThe password is summer.\n")),
        ("d26-html-file.eml", phish, strong("Open the page.\n\nAttachment: statement.html (text/html)\n")),
        ("d27-tld-swap.eml", phish, strong("Verify your account.\n\nhttps://microsoft.co/login\n")),
        ("d28-typosquat.eml", phish, strong("Verify your account.\n\nhttps://amazom.com/orders\n")),
        ("d29-combo.eml", phish, strong("Verify your account.\n\nhttps://amazon-support.net/login\n")),
        ("d30-subdomain.eml", phish, strong("Verify your account.\n\nhttps://paypal.com.secure-login.io/web\n")),
        ("d31-reset.eml", real, render(subject="Password reset", sender="IT <it@company.com>", auth_header=auth("pass", "company.com"), body="Ada, reset your password here when you are ready.\n\nhttps://company.com/reset\n")),
        ("d32-newsletter.eml", real, render(subject="Weekly", sender="News <news@harbor-letter.com>", auth_header=auth("pass", "harbor-letter.com"), body="Dear user, here is the briefing.\n\nhttps://bit.ly/harbor-week\n")),
        ("d33-pdf.eml", real, render(subject="Invoice", sender="Billing <billing@northwind-supply.com>", auth_header=auth("pass", "northwind-supply.com"), body="Ada, the invoice is attached.\n\nAttachment: invoice.pdf (application/pdf)\n")),
        ("d34-maintenance.eml", real, render(subject="Maintenance", sender="IT <it@company.com>", auth_header=auth("pass", "company.com"), body="Ada, we will restart the directory this evening. No action is needed.")),
        ("d35-shipping.eml", real, render(subject="Parcel", sender="Parcel Route <updates@parcel-route.com>", auth_header=auth("pass", "parcel-route.com"), body="Ada, the parcel is on the way.\n\nhttps://parcel-route.com/track/88\n")),
        ("d36-softfail.eml", real, render(subject="Notes", sender="Priya Shah <priya.shah@company.com>", auth_header=auth("softfail", "company.com"), body="Ada, the project notes are in the folder.\n\nhttps://company.com/notes\n")),
        ("d37-benefits.eml", real, render(subject="Benefits", sender="People Team <people@company.com>", auth_header=auth("pass", "company.com"), body="Ada, the benefits guide is updated on the intranet.")),
        ("d38-compromised.eml", phish, render(subject="Confirm", sender="IT Helpdesk <it@company.com>", auth_header=auth("pass", "company.com"), body="Dear user, your account will be suspended within 24 hours. Verify your account and confirm your password.\n\nhttps://company.com/confirm\n")),
    ]
    return rows


def main() -> None:
    write_split("test", test_rows())
    write_split("dev", dev_rows())
    for name in ("untrained.yaml", "trained.yaml"):
        source = ROOT / "data" / "test" / "configs" / name
        target = ROOT / "data" / "dev" / "configs" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"wrote {len(test_rows())} test emails and {len(dev_rows())} dev emails")


if __name__ == "__main__":
    main()
