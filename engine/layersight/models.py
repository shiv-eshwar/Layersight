"""Contracts shared by the engine, the API, and the CLI."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Layer = Literal[
    "email_filter",
    "user",
    "application_control",
    "antivirus",
    "segmentation",
]
AttackVector = Literal[
    "malware_attachment",
    "malware_link",
    "credential_harvest",
    "payment_fraud",
]
Band = Literal["critical", "high", "suspicious", "low"]
Verdict = Literal["phishing", "genuine"]
AuthValue = Literal["pass", "fail", "softfail", "none"]
RiskClass = Literal[
    "executable",
    "script",
    "macro_document",
    "archive",
    "html",
    "document",
    "image",
    "other",
]
EvidenceCategory = Literal["header", "auth", "link", "domain", "content", "attachment", "trust"]


class Address(BaseModel):
    display_name: str = ""
    address: str = ""
    domain: str = ""
    registrable_domain: str = ""


class AuthResult(BaseModel):
    spf: AuthValue = "none"
    dkim: AuthValue = "none"
    dmarc: AuthValue = "none"


class Attachment(BaseModel):
    filename: str
    content_type: str = "application/octet-stream"
    extension: str = ""
    risk_class: RiskClass = "other"
    double_extension: bool = False


class ParsedLink(BaseModel):
    text: str
    href: str
    registrable_domain: str = ""


class CharDiff(BaseModel):
    char: str
    changed: bool


class LinkView(BaseModel):
    text: str
    href: str
    display_href: str
    registrable_domain: str
    similarity: float = 0.0
    closest: str | None = None
    technique: str | None = None
    candidate_label: str = ""
    closest_label: str = ""
    diff: list[CharDiff] = Field(default_factory=list)


class ParsedEmail(BaseModel):
    subject: str = ""
    date: str | None = None
    sender: Address = Field(default_factory=Address)
    reply_to: Address | None = None
    return_path: Address | None = None
    auth: AuthResult = Field(default_factory=AuthResult)
    links: list[ParsedLink] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)
    body_text: str = ""
    parse_warnings: list[str] = Field(default_factory=list)


class Evidence(BaseModel):
    rule_id: str
    category: EvidenceCategory
    title: str
    detail: str
    location: str | None = None
    contribution: float
    share: float
    user_visible: bool


class EmailAnalysis(BaseModel):
    email_id: str
    risk_score: float
    label: Verdict
    band: Band
    attack_vector: AttackVector
    vector_reason: str
    evidence: list[Evidence]
    advice: list[str]
    cue_score: float
    features: dict[str, Any]
    engine_version: str
    weights_hash: str


class Presentation(BaseModel):
    subject: str
    date: str | None
    sender: Address
    reply_to: Address | None
    return_path: Address | None
    auth: AuthResult
    mismatches: list[str]
    links: list[LinkView]
    attachments: list[Attachment]
    body_text_sanitized: str
    highlights: list[str]
    parse_warnings: list[str]


class Bundle(BaseModel):
    sha256: str
    analysis: EmailAnalysis
    presentation: Presentation


class LayerOutcome(BaseModel):
    layer: Layer
    applicable: bool
    p_stop: float
    reasons: list[str]
    entered: int
    stopped: int


class EmailSimulation(BaseModel):
    email_id: str
    attack_vector: AttackVector
    layers: list[LayerOutcome]
    passed: int
    pass_rate: float
    ci95: tuple[float, float]
    closed_form: float


class SideResult(BaseModel):
    config_name: str
    simulation: EmailSimulation


class EmailComparison(BaseModel):
    baseline: SideResult
    comparison: SideResult
    relative_reduction: float
    narrative: str
    seed: int
    runs: int
    engine_version: str
