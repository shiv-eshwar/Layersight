"""SPF, DKIM, and DMARC from Authentication-Results, with a Received-SPF fallback."""

from __future__ import annotations

import re
from email.message import EmailMessage

from layersight.models import AuthResult

_METHOD = re.compile(
    r"(?i)\b(spf|dkim|dmarc)\s*=\s*"
    r"(pass|fail|softfail|hardfail|none|neutral|temperror|permerror|bestguesspass|policy)\b"
)
_RECEIVED = re.compile(r"(?i)^\s*(pass|fail|softfail|hardfail|neutral|none|temperror|permerror)\b")


def _status(token: str) -> str:
    name = token.lower()
    if name in {"fail", "hardfail", "permerror"}:
        return "fail"
    if name == "softfail":
        return "softfail"
    if name == "pass":
        return "pass"
    return "none"


def parse_auth(message: EmailMessage) -> AuthResult:
    found: dict[str, str] = {}
    for raw in message.get_all("Authentication-Results", []) or []:
        for match in _METHOD.finditer(str(raw)):
            kind = match.group(1).lower()
            found.setdefault(kind, _status(match.group(2)))
    if "spf" not in found:
        for raw in message.get_all("Received-SPF", []) or []:
            match = _RECEIVED.search(str(raw))
            if match is not None:
                found["spf"] = _status(match.group(1))
                break
    return AuthResult(
        spf=found.get("spf", "none"),  # type: ignore[arg-type]
        dkim=found.get("dkim", "none"),  # type: ignore[arg-type]
        dmarc=found.get("dmarc", "none"),  # type: ignore[arg-type]
    )
