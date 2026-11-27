"""Authentication alignment. Users do not see these results; filters do."""

from __future__ import annotations

from layersight.features.domains import registrable_domain
from layersight.models import AuthStatus, ParsedEmail


def _matches_sender(value: str | None, sender: str) -> bool:
    if not value:
        return True
    return registrable_domain(value) == sender


def all_mechanisms_pass(parsed: ParsedEmail) -> bool:
    auth = parsed.auth
    sender = parsed.sender.registrable_domain
    if not sender:
        return False
    return (
        auth.spf is AuthStatus.PASS
        and auth.dkim is AuthStatus.PASS
        and auth.dmarc is AuthStatus.PASS
        and _matches_sender(auth.header_from, sender)
    )


def organization_aligned(parsed: ParsedEmail, freemail: frozenset[str]) -> bool:
    sender = parsed.sender.registrable_domain
    if not sender or sender in freemail:
        return False
    auth = parsed.auth
    if not _matches_sender(auth.header_from, sender):
        return False
    if auth.dmarc is AuthStatus.PASS:
        return True
    return (
        auth.spf is AuthStatus.PASS
        and auth.dkim is AuthStatus.PASS
        and auth.dmarc is not AuthStatus.FAIL
    )
