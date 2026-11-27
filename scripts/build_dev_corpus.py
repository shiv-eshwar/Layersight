"""Write the development corpus. The generated files are the canonical data.

Run from the repo root: uv run python scripts/build_dev_corpus.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EMAILS = ROOT / "data" / "dev" / "emails"
LABELS = ROOT / "data" / "dev" / "labels.csv"
COVERAGE = ROOT / "data" / "dev" / "coverage.yaml"

EXPECTED_RULES = [
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
]


def msg(headers: list[tuple[str, str]], body: str) -> str:
    lines = [f"{key}: {value}" for key, value in headers]
    text = body.strip("\n") + "\n"
    return "\n".join(lines) + "\n\n" + text


def auth(spf: str, dkim: str, dmarc: str, mailfrom: str, header_from: str) -> str:
    return (
        "mx.contoso.example; "
        f"spf={spf} smtp.mailfrom={mailfrom}; "
        f"dkim={dkim} header.d={header_from}; "
        f"dmarc={dmarc} header.from={header_from}"
    )


def base(
    subject: str, from_header: str, reply_to: str, return_path: str, auth_value: str
) -> list[tuple[str, str]]:
    return [
        ("From", from_header),
        ("Reply-To", reply_to),
        ("Return-Path", return_path),
        ("To", "Alex Rivera <alex.rivera@contoso.example>"),
        ("Date", "Thu, 14 Nov 2026 10:24:00 +0000"),
        ("Message-ID", f"<{subject.split()[0].lower()}@corpus.layersight>"),
        ("MIME-Version", "1.0"),
        ("Content-Type", "text/plain; charset=utf-8"),
        ("Authentication-Results", auth_value),
        ("Subject", subject),
    ]


CORPUS: list[dict[str, object]] = []


def add(
    filename: str,
    label: str,
    rules: list[str],
    body_headers: list[tuple[str, str]],
    body: str,
    hard: str | None = None,
    raw: str | None = None,
) -> None:
    CORPUS.append(
        {
            "filename": filename,
            "label": label,
            "rules": rules,
            "hard": hard,
            "raw": raw if raw is not None else msg(body_headers, body),
        }
    )


add(
    "01-reply-to-mismatch.eml",
    "phishing",
    ["H01", "A03", "C02", "C04"],
    base(
        "Action required: verify your account",
        '"Microsoft Account Team" <security@microsoft.com>',
        "support@ms-account-verify.com",
        "<bounce@ms-account-verify.com>",
        auth("fail", "fail", "fail", "ms-account-verify.com", "microsoft.com"),
    ),
    """
Dear user,

Your Microsoft account will be locked in 24 hours unless you verify your account.
Open https://microsoft.com/verify and confirm your password.

Microsoft Account Team
""",
)

add(
    "02-display-name-freemail.eml",
    "phishing",
    ["H02", "H04"],
    base(
        "Payroll change for Alex Rivera",
        '"Contoso Payroll" <contoso.payroll@gmail.com>',
        "contoso.payroll@gmail.com",
        "<contoso.payroll@gmail.com>",
        auth("pass", "pass", "pass", "gmail.com", "gmail.com"),
    ),
    """
Alex,

This is Priya from payroll. Reply with the bank details we should use for your November salary.
The old account on file is no longer valid.

Priya Shah
Contoso Payroll
""",
)

add(
    "03-return-path-spf-fail.eml",
    "phishing",
    ["H03", "A01"],
    base(
        "Documents for your signature",
        "DocuSign <dse@docusign.com>",
        "dse@docusign.com",
        "<mailer@signature-docs.example>",
        auth("fail", "none", "none", "signature-docs.example", "docusign.com"),
    ),
    """
You have a document waiting. Review it at https://docusign.com/signing/8f3a.
""",
)

add(
    "04-dkim-fail-lookalike.eml",
    "phishing",
    ["A02", "L02"],
    base(
        "Unusual sign-in to your account",
        "PayPal <service@paypal.com>",
        "service@paypa1.com",
        "<bounce@paypa1.com>",
        auth("softfail", "fail", "fail", "paypa1.com", "paypal.com"),
    ),
    """
We noticed a sign-in from a new device. If this was not you, secure your account:
https://paypa1.com/signin
""",
)

DECEPTIVE_LINK = """\
From: "Amazon Account" <account-update@amazon.com>
Reply-To: help@amazom.com
Return-Path: <bounce@amazom.com>
To: Alex Rivera <alex.rivera@contoso.example>
Date: Thu, 14 Nov 2026 10:24:00 +0000
Message-ID: <link-text@corpus.layersight>
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="bound-link"
Authentication-Results: mx.contoso.example; spf=fail smtp.mailfrom=amazom.com; dkim=fail header.d=amazon.com; dmarc=fail header.from=amazon.com
Subject: Your Amazon order needs confirmation

--bound-link
Content-Type: text/plain; charset=utf-8

Dear user,

Confirm your order: https://amazon.com/orders/confirm

--bound-link
Content-Type: text/html; charset=utf-8

<p>Dear user,</p>
<p>Confirm your order:
<a href="http://amazom.com/orders/confirm">https://amazon.com/orders/confirm</a>
</p>

--bound-link--
"""

add(
    "05-deceptive-link-text.eml",
    "phishing",
    ["L01", "L02"],
    [],
    "",
    raw=DECEPTIVE_LINK,
)

add(
    "06-ip-address-url.eml",
    "phishing",
    ["L03", "C02"],
    base(
        "Mailbox almost full",
        "IT Helpdesk <helpdesk@contoso.example>",
        "helpdesk@mailbox-quota.example",
        "<helpdesk@mailbox-quota.example>",
        auth("fail", "none", "fail", "mailbox-quota.example", "contoso.example"),
    ),
    """
Dear user,

Your mailbox is 99% full and incoming mail will be deleted. Verify your account at
http://203.0.113.50/webmail/login before the end of the day.
""",
)

add(
    "07-punycode-domain.eml",
    "phishing",
    ["L04"],
    base(
        "Shared a folder with you",
        "Dropbox <no-reply@dropbox.com>",
        "no-reply@xn--drpbox-n0a.com",
        "<bounce@xn--drpbox-n0a.com>",
        auth("fail", "fail", "fail", "xn--drpbox-n0a.com", "dropbox.com"),
    ),
    """
Alex Rivera shared "Q4 forecast" with you.
Open it: http://xn--drpbox-n0a.com/folder/q4
""",
)

add(
    "08-shortener-and-threat.eml",
    "phishing",
    ["L05", "C05"],
    base(
        "Final notice: account suspended",
        "Netflix <info@netflix.com>",
        "billing@netflix-help.example",
        "<billing@netflix-help.example>",
        auth("fail", "none", "fail", "netflix-help.example", "netflix.com"),
    ),
    """
Your membership is suspended and will be deleted tonight.
Update your payment details: https://bit.ly/nf-restore
""",
)

add(
    "09-subdomain-abuse.eml",
    "phishing",
    ["L06"],
    base(
        "Receipt for your payment",
        "PayPal Service <receipts@paypal.com>",
        "receipts@paypal.com.secure-login.io",
        "<receipts@paypal.com.secure-login.io>",
        auth("pass", "none", "fail", "secure-login.io", "paypal.com"),
    ),
    """
You sent a payment of $480.00.
If you did not authorize this, cancel it at https://paypal.com.secure-login.io/dispute
""",
    hard="positive",
)

add(
    "10-suspicious-tld.eml",
    "phishing",
    ["L07"],
    base(
        "Voice message from your manager",
        "Teams <noreply@microsoft.com>",
        "noreply@teams-voice.tk",
        "<noreply@teams-voice.tk>",
        auth("fail", "none", "fail", "teams-voice.tk", "microsoft.com"),
    ),
    """
You have a new voice message (0:42).
Listen: https://teams-voice.tk/play/9182
""",
)

add(
    "11-http-login.eml",
    "phishing",
    ["L08", "C02"],
    base(
        "Sign-in from a new browser",
        "Google <accounts@google.com>",
        "accounts@google-protect.example",
        "<accounts@google-protect.example>",
        auth("fail", "fail", "fail", "google-protect.example", "google.com"),
    ),
    """
A new browser signed in to your account. If this was not you, verify your account here:
http://accounts.google-protect.example/login
""",
)

add(
    "12-unrelated-link-domain.eml",
    "phishing",
    ["L09"],
    base(
        "Your statement is ready",
        "First National <statements@firstnational.example>",
        "statements@firstnational.example",
        "<statements@firstnational.example>",
        auth("pass", "pass", "pass", "firstnational.example", "firstnational.example"),
    ),
    """
Your October statement is ready to view.
Download it from our partner site: https://statements-cdn.example/fn/october
""",
)

add(
    "13-bec-wire.eml",
    "phishing",
    ["C03", "H02"],
    base(
        "Wire for the acquisition, today",
        '"Alex Rivera, CFO" <a.rivera@contoso-payments.com>',
        "a.rivera@contoso-payments.com",
        "<a.rivera@contoso-payments.com>",
        auth("pass", "pass", "pass", "contoso-payments.com", "contoso-payments.com"),
    ),
    """
I am in a meeting and cannot talk.

Please wire $48,600 to the account below before 16:00. This is for the acquisition deposit
and it cannot wait. Reply when it is sent.

Bank: Harbor Mutual
Account name: Northline Holdings
Account number: 883021194
Routing: 021000021

Alex Rivera
Chief Financial Officer
""",
    hard="positive",
)

add(
    "14-urgency-and-threat.eml",
    "phishing",
    ["C01", "C05"],
    base(
        "Final notice before your files are deleted",
        "OneDrive <notify@microsoft.com>",
        "notify@onedrive-alert.example",
        "<notify@onedrive-alert.example>",
        auth("fail", "none", "fail", "onedrive-alert.example", "microsoft.com"),
    ),
    """
This is your final notice. Your files will be deleted within 24 hours because the
storage payment failed. Act immediately: https://onedrive-alert.example/renew
""",
)

add(
    "15-executable-attachment.eml",
    "phishing",
    ["T01"],
    base(
        "Scanner driver you requested",
        "IT Support <it-support@contoso.example>",
        "it-support@driver-updates.example",
        "<it-support@driver-updates.example>",
        auth("fail", "none", "fail", "driver-updates.example", "contoso.example"),
    ),
    """
As requested, the scanner driver is attached. Run it on your laptop today.

Attachment: SecureScanner_Setup.exe (application/x-msdownload)
""",
)

add(
    "16-double-extension.eml",
    "phishing",
    ["T02"],
    base(
        "Invoice for last week's order",
        "Accounts Payable <ap@northwind.example>",
        "ap@northwind-billing.example",
        "<ap@northwind-billing.example>",
        auth("pass", "none", "none", "northwind-billing.example", "northwind-billing.example"),
    ),
    """
Please review the attached invoice and confirm the total.

Attachment: invoice.pdf.exe (application/x-msdownload)
""",
)

add(
    "17-macro-document.eml",
    "phishing",
    ["T03"],
    base(
        "Please enable editing to view the offer",
        "People Team <jobs@contoso.example>",
        "jobs@careers-contoso.example",
        "<jobs@careers-contoso.example>",
        auth("fail", "none", "fail", "careers-contoso.example", "contoso.example"),
    ),
    """
Your offer letter is attached. If Word shows a yellow bar, choose Enable Content to read it.

Attachment: Offer-Letter.docm (application/vnd.ms-word.document.macroEnabled.12)
""",
)

add(
    "18-password-archive.eml",
    "phishing",
    ["T04"],
    base(
        "Encrypted payslips for the team",
        "Payroll <payroll@contoso.example>",
        "payroll@contoso-hr.example",
        "<payroll@contoso-hr.example>",
        auth("fail", "none", "fail", "contoso-hr.example", "contoso.example"),
    ),
    """
The November payslips are in the attached archive. The archive password is payslip2026.

Attachment: payslips.zip (application/zip)
""",
)

add(
    "19-html-attachment.eml",
    "phishing",
    ["T05", "C01"],
    base(
        "You have a new voicemail",
        "Phone System <voicemail@contoso.example>",
        "voicemail@pbx-notify.example",
        "<voicemail@pbx-notify.example>",
        auth("fail", "none", "fail", "pbx-notify.example", "contoso.example"),
    ),
    """
A caller left a message at 09:14. Open the attachment immediately or it will expire within 24 hours.

Attachment: voicemail.html (text/html)
""",
)

add(
    "20-compromised-mailbox.eml",
    "phishing",
    ["A04", "C02", "L07"],
    base(
        "Please re-confirm payroll before Friday",
        "Jane Okonkwo <jane.okonkwo@contoso.example>",
        "jane.okonkwo@contoso.example",
        "<jane.okonkwo@contoso.example>",
        auth("pass", "pass", "pass", "contoso.example", "contoso.example"),
    ),
    """
Hi Alex,

Payroll asked me to have everyone verify your account on the new portal before Friday,
or the November payment will be held. It takes a minute:

https://contoso.example.payroll-update.tk/login

Thanks,
Jane
""",
    hard="positive",
)

SOFTFAIL = msg(
    [
        ("From", "Shipping Desk <desk@fedex.com>"),
        ("Reply-To", "desk@fedex-hold.example"),
        ("Return-Path", "<desk@fedex-hold.example>"),
        ("To", "Alex Rivera <alex.rivera@contoso.example>"),
        ("Date", "Thu, 14 Nov 2026 11:02:00 +0000"),
        ("Message-ID", "<softfail@corpus.layersight>"),
        ("MIME-Version", "1.0"),
        ("Content-Type", "text/plain; charset=utf-8"),
        (
            "Received-SPF",
            'softfail (spf check failed) identity=mailfrom; envelope-from="desk@fedex-hold.example"; receiver=mx.contoso.example',
        ),
        ("Subject", "Delivery held for a fee"),
    ],
    """
Your parcel is held at the depot. Pay the release fee to schedule delivery:
https://fedex-hold.example/release
""",
)
add("21-spf-softfail.eml", "phishing", ["A01"], [], "", raw=SOFTFAIL)

add(
    "22-malware-download-link.eml",
    "phishing",
    ["L02"],
    base(
        "Remittance advice attached as a download",
        "Accounts <billing@adobe.com>",
        "billing@adobe-docs.example",
        "<billing@adobe-docs.example>",
        auth("fail", "fail", "fail", "adobe-docs.example", "adobe.com"),
    ),
    """
Download the remittance advice and open it on your computer:
https://ad0be-docs.example/files/remittance.exe
""",
)

add(
    "23-gift-card-request.eml",
    "phishing",
    ["C03", "H04"],
    base(
        "Need a favor before the client call",
        '"Priya Shah" <priya.shah.contoso@outlook.com>',
        "priya.shah.contoso@outlook.com",
        "<priya.shah.contoso@outlook.com>",
        auth("pass", "pass", "pass", "outlook.com", "outlook.com"),
    ),
    """
Alex, I am about to walk into a client meeting and cannot get to a store.

Please buy four $100 gift cards and reply with the codes. I will reimburse you today.
Do this now if you can.

Priya Shah
VP, Customer Operations
""",
)

add(
    "24-dkim-none.eml",
    "phishing",
    ["A02"],
    base(
        "Shared a document for review",
        "Adobe Sign <sign@adobe.com>",
        "sign@adobe-esign.example",
        "<sign@adobe-esign.example>",
        auth("fail", "none", "fail", "adobe-esign.example", "adobe.com"),
    ),
    """
A document is waiting for your signature.
Review it: https://adobe-esign.example/sign/441
""",
)

add(
    "25-genuine-password-reset.eml",
    "genuine",
    ["A04", "G01", "G02", "C01", "C02"],
    base(
        "Reset your Contoso password",
        "IT Service Desk <it-support@contoso.example>",
        "it-support@contoso.example",
        "<bounces@contoso.example>",
        auth("pass", "pass", "pass", "contoso.example", "contoso.example"),
    ),
    """
Hello Alex,

We received a request to reset your password. You can choose a new one within 24 hours:
https://password.contoso.example/reset/9c2e

If you did not ask for this, you can ignore the message. Your password will not change.

IT Service Desk
Contoso
""",
    hard="negative",
)

add(
    "26-genuine-newsletter.eml",
    "genuine",
    ["L05", "L09"],
    base(
        "Northwind Notes, November",
        "Northwind Notes <news@northwind.example>",
        "news@northwind.example",
        "<news@northwind.example>",
        auth("pass", "pass", "pass", "northwind.example", "northwind.example"),
    ),
    """
Hello Alex,

Three stories from the Northwind team this month, plus the date of the open house.

Read the issue: https://news.northwind.example/issue/12
A shorter link, if you need one: https://bit.ly/nw-nov
This copy was also archived by our mail vendor: https://trk.mailvendor.net/c/12

You are receiving this because you subscribed at the open house.
Unsubscribe: https://news.northwind.example/unsubscribe
""",
    hard="negative",
)

PDF_INVOICE = """\
From: Accounts <billing@northwind.example>
Reply-To: billing@northwind.example
Return-Path: <billing@northwind.example>
To: Alex Rivera <alex.rivera@contoso.example>
Date: Tue, 11 Nov 2026 15:03:00 +0000
Message-ID: <invoice-2041@northwind.example>
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="bound-pdf"
Authentication-Results: mx.contoso.example; spf=pass smtp.mailfrom=northwind.example; dkim=pass header.d=northwind.example; dmarc=pass header.from=northwind.example
Subject: Invoice 2041 from Northwind

--bound-pdf
Content-Type: text/plain; charset=utf-8

Hello Alex,

Invoice 2041 for the October stationery order is attached and is also online:
https://billing.northwind.example/invoices/2041

Payment is due 11 December. The purchase order on the invoice is PO-1884.

Northwind Accounts

--bound-pdf
Content-Type: application/pdf; name="invoice-2041.pdf"
Content-Disposition: attachment; filename="invoice-2041.pdf"
Content-Transfer-Encoding: base64

JVBERg==

--bound-pdf--
"""

add(
    "27-genuine-pdf-invoice.eml",
    "genuine",
    [],
    [],
    "",
    hard="negative",
    raw=PDF_INVOICE,
)

add(
    "28-genuine-it-urgency.eml",
    "genuine",
    ["C01", "G01"],
    base(
        "VPN unavailable tonight from 22:00",
        "IT Operations <it-ops@contoso.example>",
        "it-ops@contoso.example",
        "<it-ops@contoso.example>",
        auth("pass", "pass", "pass", "contoso.example", "contoso.example"),
    ),
    """
Hello,

The office VPN will be unavailable tonight from 22:00 to 23:30 for a firmware update.
Please save your work and disconnect before then. Remote desktop sessions will drop.

No action is required after the window. Status, if you want it:
https://status.contoso.example/vpn

IT Operations
""",
    hard="negative",
)

add(
    "29-genuine-shipping.eml",
    "genuine",
    ["G02"],
    base(
        "Your package is out for delivery",
        "DHL Express <noreply@dhl.com>",
        "noreply@dhl.com",
        "<noreply@dhl.com>",
        auth("pass", "pass", "pass", "dhl.com", "dhl.com"),
    ),
    """
Hello Alex Rivera,

Shipment 1234567890 is out for delivery today between 13:00 and 17:00.
Track it: https://www.dhl.com/track?id=1234567890

DHL Express
""",
    hard="negative",
)

add(
    "30-genuine-intranet-links.eml",
    "genuine",
    ["A04", "G01", "G02"],
    base(
        "Benefits enrollment closes Friday",
        "People Team <people@contoso.example>",
        "people@contoso.example",
        "<people@contoso.example>",
        auth("pass", "pass", "pass", "contoso.example", "contoso.example"),
    ),
    """
Hello Alex,

Benefits enrollment closes on Friday 21 November. You can review the plans and make
your choices on the intranet. Nothing in this message asks you to send a password
or a payment.

Plans: https://intranet.contoso.example/benefits
Enrollment: https://contoso.example/benefits/enroll

People Team
""",
)

add(
    "31-genuine-meeting.eml",
    "genuine",
    [],
    base(
        "Design review moved to 15:00",
        "Samir Iqbal <samir.iqbal@contoso.example>",
        "samir.iqbal@contoso.example",
        "<samir.iqbal@contoso.example>",
        auth("pass", "pass", "pass", "contoso.example", "contoso.example"),
    ),
    """
Alex,

The design review is moving from 14:00 to 15:00 because the room was double booked.
Same agenda. I will bring the printed mockups.

Samir
""",
)

add(
    "32-genuine-hr-policy.eml",
    "genuine",
    ["G01"],
    base(
        "Updated travel policy, effective 1 December",
        "People Operations <people-ops@contoso.example>",
        "people-ops@contoso.example",
        "<people-ops@contoso.example>",
        auth("pass", "pass", "pass", "contoso.example", "contoso.example"),
    ),
    """
Hello,

The travel policy has been updated. Bookings over $1,000 now need a manager's approval
before the ticket is purchased. The page on the intranet has the full text.

https://intranet.contoso.example/policies/travel

People Operations
""",
)

add(
    "33-genuine-receipt.eml",
    "genuine",
    ["G02"],
    base(
        "Your receipt from Northwind Cafe",
        "Northwind Cafe <receipts@northwind.example>",
        "receipts@northwind.example",
        "<receipts@northwind.example>",
        auth("pass", "pass", "pass", "northwind.example", "northwind.example"),
    ),
    """
Hello Alex,

Thanks for your visit. This receipt is for $14.80 on 13 November.
View it: https://receipts.northwind.example/r/44821

Northwind Cafe
""",
)

add(
    "34-genuine-colleague.eml",
    "genuine",
    ["G01"],
    base(
        "Notes from the vendor call",
        "Leila Haddad <leila.haddad@contoso.example>",
        "leila.haddad@contoso.example",
        "<leila.haddad@contoso.example>",
        auth("pass", "pass", "pass", "contoso.example", "contoso.example"),
    ),
    """
Alex,

I wrote up the vendor call. Two things we agreed: they will send the revised quote by
Wednesday, and we will not share the pricing with the other bidder. The notes are in
our team folder on the intranet.

https://intranet.contoso.example/teams/procurement/vendor-call

Leila
""",
)

add(
    "35-genuine-github-notification.eml",
    "genuine",
    ["G02", "A04"],
    base(
        "Re: [contoso/portal] Fix the empty triage state (#128)",
        "GitHub <notifications@github.com>",
        "notifications@github.com",
        "<notifications@github.com>",
        auth("pass", "pass", "pass", "github.com", "github.com"),
    ),
    """
@leila commented on a pull request you review.

"The empty state should tell people to upload emails, and the button should go to triage."

View the comment: https://github.com/contoso/portal/pull/128#issuecomment-1

You are receiving this because you are subscribed to this thread.
Unsubscribe: https://github.com/notifications/unsubscribe/thread
""",
)

add(
    "36-genuine-vendor-quote.eml",
    "genuine",
    [],
    base(
        "Revised quote for the badge printer",
        "Northwind Sales <sales@northwind.example>",
        "sales@northwind.example",
        "<sales@northwind.example>",
        auth("pass", "pass", "pass", "northwind.example", "northwind.example"),
    ),
    """
Hello Alex,

Attached in spirit, and also linked, is the revised quote we discussed. The unit price
is unchanged. Delivery is three weeks from a purchase order.

Quote: https://sales.northwind.example/quotes/7781

I am happy to walk through it on Thursday.

Northwind Sales
""",
)


def main() -> None:
    seen = {item["filename"] for item in CORPUS}
    if len(seen) != len(CORPUS):
        raise SystemExit("duplicate filename in the corpus")
    covered: set[str] = set()
    for item in CORPUS:
        covered.update(item["rules"])  # type: ignore[arg-type]
    missing = [rule for rule in EXPECTED_RULES if rule not in covered]
    if missing:
        raise SystemExit(f"rules with no email: {missing}")

    EMAILS.mkdir(parents=True, exist_ok=True)
    for old in EMAILS.glob("*.eml"):
        old.unlink()
    for item in CORPUS:
        (EMAILS / str(item["filename"])).write_text(str(item["raw"]), encoding="utf-8")

    with LABELS.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["filename", "label"])
        for item in CORPUS:
            writer.writerow([item["filename"], item["label"]])

    by_rule: dict[str, list[str]] = {rule: [] for rule in EXPECTED_RULES}
    hard_positive: list[str] = []
    hard_negative: list[str] = []
    for item in CORPUS:
        filename = str(item["filename"])
        for rule in item["rules"]:  # type: ignore[union-attr]
            by_rule[str(rule)].append(filename)
        if item["hard"] == "positive":
            hard_positive.append(filename)
        elif item["hard"] == "negative":
            hard_negative.append(filename)

    lines = [
        "# Generated by scripts/build_dev_corpus.py. Do not edit by hand.",
        "rules:",
    ]
    for rule in EXPECTED_RULES:
        files = ", ".join(by_rule[rule])
        lines.append(f"  {rule}: [{files}]")
    lines.append("hard_positives:")
    for filename in hard_positive:
        lines.append(f"  - {filename}")
    lines.append("hard_negatives:")
    for filename in hard_negative:
        lines.append(f"  - {filename}")
    lines.append("")
    COVERAGE.write_text("\n".join(lines), encoding="utf-8")
    phishing = sum(1 for item in CORPUS if item["label"] == "phishing")
    genuine = sum(1 for item in CORPUS if item["label"] == "genuine")
    print(f"wrote {len(CORPUS)} emails ({phishing} phishing, {genuine} genuine)")


if __name__ == "__main__":
    main()
