"""Curated phrases. Each cue fires at most once per email."""

from __future__ import annotations

import re

URGENCY: tuple[str, ...] = (
    "within 24 hours",
    "within 48 hours",
    "respond immediately",
    "final notice",
    "last warning",
    "act now",
    "expires today",
    "right away",
    "as soon as possible",
    "immediately",
    "urgently",
    "urgent",
)
CREDENTIAL: tuple[str, ...] = (
    "verify your account",
    "confirm your password",
    "reset your password",
    "update your password",
    "re-enter your password",
    "sign in to your account",
    "log in to your account",
    "login to your account",
    "enter your credentials",
    "confirm your identity",
    "validate your account",
)
PAYMENT: tuple[str, ...] = (
    "wire transfer",
    "wire the funds",
    "wire funds",
    "gift cards",
    "gift card",
    "new bank details",
    "updated bank details",
    "bank account details",
    "routing number",
    "change of bank",
    "wire",
)
GREETING: tuple[str, ...] = (
    "dear valued customer",
    "dear account holder",
    "dear sir or madam",
    "dear sir/madam",
    "dear customer",
    "dear client",
    "dear member",
    "dear user",
)
THREAT: tuple[str, ...] = (
    "permanently disabled",
    "permanently deleted",
    "account suspended",
    "has been suspended",
    "will be suspended",
    "account locked",
    "has been locked",
    "will be locked",
    "will be deleted",
    "will be closed",
    "account closure",
    "suspended",
    "locked",
    "deleted",
)
_PASSWORD = re.compile(r"\b(password|passcode|passphrase|pwd)\b", re.IGNORECASE)


def searchable(subject: str, body: str) -> str:
    return f"{subject}\n{body}"


def first_phrase(text: str, phrases: tuple[str, ...]) -> str | None:
    lowered = text.lower()
    for phrase in sorted(phrases, key=len, reverse=True):
        if re.search(rf"\b{re.escape(phrase)}\b", lowered):
            return phrase
    return None


def password_mentioned(text: str) -> bool:
    return _PASSWORD.search(text) is not None
