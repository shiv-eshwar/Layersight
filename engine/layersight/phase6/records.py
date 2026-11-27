"""One message after it has been read and scored."""

from __future__ import annotations

from dataclasses import dataclass

from layersight.models import EmailAnalysis
from layersight.phase6.read import Observation


@dataclass(frozen=True)
class ScoredMail:
    email_id: str
    subject: str
    sender: str
    true_label: str | None
    analysis: EmailAnalysis
    observed: Observation
