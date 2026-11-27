"""Attack vector: the first matching harm this email could cause."""

from __future__ import annotations

import re

from layersight.models import AttackVector, Attachment, LinkView

_RISKY = {"executable", "script", "macro_document", "archive", "html"}
_PATH_RISK = (".exe", ".js", ".vbs", ".ps1", ".hta", ".docm", ".xlsm", ".zip", ".html", ".htm", ".iso")
_DOWNLOAD = re.compile(r"\b(download|install)\b", re.IGNORECASE)
_LOGIN = re.compile(r"\b(sign in|log in|login|verify)\b", re.IGNORECASE)


def classify(
    attachments: list[Attachment],
    links: list[LinkView],
    *,
    credential: bool,
    payment: bool,
    max_lookalike: float,
    body: str,
) -> tuple[AttackVector, str]:
    if any(item.risk_class in _RISKY for item in attachments):
        return (
            "malware_attachment",
            "The email carries a risky attachment. Endpoint controls can see this kind of attack.",
        )
    if _malware_link(links, body):
        return (
            "malware_link",
            "The email points at a download. Endpoint controls can see this kind of attack.",
        )
    lookalike = max_lookalike >= 0.80
    if links and (credential or lookalike or _LOGIN.search(body)):
        return (
            "credential_harvest",
            "The email asks someone to sign in or follow a look-alike link. Antivirus and application control do not apply.",
        )
    risky = any(item.risk_class in _RISKY for item in attachments)
    if not links and not risky and payment:
        return (
            "payment_fraud",
            "The email asks for a payment and has no malicious file. Only the filter and the recipient can stop it.",
        )
    if links:
        return (
            "credential_harvest",
            "No malware or payment request was found. The email has links, so the recorded vector is credential harvesting.",
        )
    return (
        "payment_fraud",
        "No link or malware was found. The recorded vector is payment fraud, which only the filter and the recipient can stop.",
    )


def _malware_link(links: list[LinkView], body: str) -> bool:
    for link in links:
        path = link.href.lower().split("?", 1)[0]
        if path.endswith(_PATH_RISK):
            return True
    if links and _DOWNLOAD.search(body):
        return True
    return False
