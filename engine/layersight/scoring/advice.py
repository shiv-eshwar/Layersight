"""Plain-language advice, at most three findings plus a closing action."""

from __future__ import annotations

from layersight.models import ParsedEmail
from layersight.scoring.finding import Finding


def build_advice(label: str, findings: list[Finding], parsed: ParsedEmail) -> list[str]:
    if label == "genuine":
        return [
            "No strong warning signs. Still confirm unexpected requests for money or credentials through a separate channel."
        ]
    lines: list[str] = []
    for finding in sorted(findings, key=lambda item: item.contribution, reverse=True):
        if len(lines) >= 3:
            break
        line = _line(finding, parsed)
        if line and line not in lines:
            lines.append(line)
    lines.append("Report it with the Report Phish button, then delete it.")
    return lines


def _line(finding: Finding, parsed: ParsedEmail) -> str | None:
    variables = finding.variables
    if finding.rule_id == "H01":
        return (
            f"Replies would go to {variables.get('reply_domain', 'another domain')}, "
            f"not {variables.get('from_domain', 'the sender')}. Don't reply; contact the sender through a channel you already know."
        )
    if finding.rule_id in {"L01", "L02"}:
        domain = variables.get("domain", "a different site")
        brand = variables.get("brand_domain", "the real site")
        return (
            f"The link goes to {domain}, which imitates {brand}. Don't click it. "
            f"Type {brand} into your browser instead."
        )
    if finding.rule_id in {"T01", "T02"}:
        filename = variables.get("filename") or _filename(parsed)
        return f"Don't open {filename}. Real invoices and documents are never executable files."
    if finding.rule_id == "A03":
        return "This message failed sender authentication, so the sender address is probably forged."
    if finding.rule_id == "C02":
        return "Don't type your password because this email asked you to. Open the service by typing its address yourself."
    if finding.rule_id == "C03":
        return "Don't send money or change bank details because of this email. Confirm with a number you already have."
    if finding.rule_id == "T03":
        return f"Don't enable macros in {variables.get('filename', 'the attachment')}. View the document in a browser preview instead."
    if finding.contribution <= 0:
        return None
    if finding.user_visible:
        return finding.detail
    return None


def _filename(parsed: ParsedEmail) -> str:
    if parsed.attachments:
        return parsed.attachments[0].filename
    return "the attachment"
