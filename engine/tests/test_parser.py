from email.message import EmailMessage

from layersight.scoring.analyze import analyze_email


def test_attachment_payload_is_not_read() -> None:
    message = EmailMessage()
    message["From"] = "Billing <billing@northwind-supply.com>"
    message["To"] = "Ada <ada@company.com>"
    message["Subject"] = "Invoice"
    message.set_content("The invoice is attached.")
    message.add_attachment(
        b"UNIQUE_PAYLOAD_MARKER",
        maintype="application",
        subtype="octet-stream",
        filename="invoice.pdf.exe",
    )
    bundle = analyze_email(message.as_string())
    assert "UNIQUE_PAYLOAD_MARKER" not in bundle.presentation.body_text_sanitized
    attachment = bundle.presentation.attachments[0]
    assert attachment.filename == "invoice.pdf.exe"
    assert attachment.risk_class == "executable"
    assert attachment.double_extension is True


def test_missing_blank_line_still_parses() -> None:
    raw = "From: IT <it@company.com>\nSubject: Hello\nTo: Ada <ada@company.com>\nThis is the body.\n"
    bundle = analyze_email(raw)
    assert bundle.presentation.subject == "Hello"
    assert "This is the body." in bundle.presentation.body_text_sanitized
    assert bundle.presentation.parse_warnings
