"""Header comparisons used by H01–H04."""

from __future__ import annotations

import re

from layersight.models import MailAddress, ParsedEmail
from layersight.reference_data import Brand

_ROLE = re.compile(
    r"\b(chief executive|chief financial|chief technology|ceo|cfo|cto|coo|"
    r"president|vice president|director|payroll|help\s?desk|it support|"
    r"security team|account team|human resources)\b",
    re.IGNORECASE,
)
_ORG_CLAIM = re.compile(
    r"\b(incorporated|corporation|company|department|helpdesk|official|llc|ltd)\b",
    re.IGNORECASE,
)


def reply_to_mismatch(parsed: ParsedEmail) -> MailAddress | None:
    sender = parsed.sender.registrable_domain
    if not sender:
        return None
    for address in parsed.reply_to:
        if address.registrable_domain and address.registrable_domain != sender:
            return address
    return None


def return_path_mismatch(parsed: ParsedEmail) -> MailAddress | None:
    sender = parsed.sender.registrable_domain
    return_path = parsed.return_path
    if return_path is None or not sender or not return_path.registrable_domain:
        return None
    if return_path.registrable_domain != sender:
        return return_path
    return None


def brands_in_display(name: str, brands: tuple[Brand, ...]) -> list[Brand]:
    haystack = name.lower()
    found: list[Brand] = []
    for brand in brands:
        for alias in brand.aliases:
            if re.search(rf"\b{re.escape(alias)}\b", haystack):
                found.append(brand)
                break
    return found


def unmatched_brand(name: str, sender_domain: str, brands: tuple[Brand, ...]) -> Brand | None:
    for brand in brands_in_display(name, brands):
        if sender_domain not in brand.domains:
            return brand
    return None


def role_claim(name: str) -> str | None:
    match = _ROLE.search(name)
    if match is None:
        return None
    return match.group(0)


def org_claim(name: str) -> str | None:
    match = _ORG_CLAIM.search(name)
    if match is None:
        return None
    return match.group(0)
