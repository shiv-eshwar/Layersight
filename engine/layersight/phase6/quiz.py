"""Quiz questions generated from scored messages, and the score of an attempt."""

from __future__ import annotations

import hashlib
import random
import re

from layersight.phase6.lookup import registrable_domain
from layersight.phase6.models import AnswerIn, AnswerResult, QuizGrade, QuizOption, QuizQuestion
from layersight.phase6.records import ScoredMail
from layersight.textutil import host_of

_DISTRACTORS = (
    "The message was sent on a weekday",
    "The subject line is short",
    "The message includes a signature",
    "The recipient's company is named",
    "The date uses a four-digit year",
)
_KIND_LABELS = {
    "phish_or_legit": "Phishing or legitimate",
    "most_suspicious": "Most suspicious element",
    "link_destination": "Link destination",
}
_URL = re.compile(r"https?://\S+", re.IGNORECASE)


def generate(mails: list[ScoredMail], n: int = 10, seed: int = 42) -> list[QuizQuestion]:
    pools: dict[str, list[QuizQuestion]] = {
        "phish_or_legit": [],
        "most_suspicious": [],
        "link_destination": [],
    }
    for mail in mails:
        verdict = _verdict(mail)
        pools["phish_or_legit"].append(_verdict_question(mail, verdict))
        suspicious = _suspicious_question(mail, seed)
        if suspicious is not None:
            pools["most_suspicious"].append(suspicious)
        link = _link_question(mail, seed)
        if link is not None:
            pools["link_destination"].append(link)
    rng = random.Random(seed)
    for questions in pools.values():
        rng.shuffle(questions)
    picked: list[QuizQuestion] = []
    while len(picked) < n and any(pools.values()):
        for kind in ("phish_or_legit", "most_suspicious", "link_destination"):
            if pools[kind] and len(picked) < n:
                picked.append(pools[kind].pop())
    return picked


def grade(
    dataset_id: str,
    mails: list[ScoredMail],
    answers: list[AnswerIn],
    n: int = 10,
    seed: int = 42,
    record: bool = False,
) -> QuizGrade:
    questions = {item.id: item for item in generate(mails, n=n, seed=seed)}
    results: list[AnswerResult] = []
    by_kind: dict[str, list[bool]] = {}
    for answer in answers:
        question = questions.get(answer.question_id)
        if question is None:
            continue
        correct = answer.chosen == question.answer_id
        by_kind.setdefault(question.kind, []).append(correct)
        results.append(
            AnswerResult(
                question_id=question.id,
                chosen=answer.chosen,
                correct=correct,
                correct_option_id=question.answer_id,
                explanation=question.explanation,
            )
        )
    total = len(results)
    correct_count = sum(1 for item in results if item.correct)
    accuracy = (correct_count / total) if total else 0.0
    weak = [
        _KIND_LABELS[kind]
        for kind, flags in by_kind.items()
        if flags and (sum(1 for flag in flags if flag) / len(flags)) < 0.7
    ]
    return QuizGrade(
        dataset_id=dataset_id,
        correct=correct_count,
        total=total,
        accuracy=accuracy,
        catch_rate=catch_rate(accuracy),
        weak_areas=weak,
        results=results,
        recorded=record,
    )


def catch_rate(accuracy: float) -> float:
    """Map a quiz accuracy onto the user-layer catch rate, inside the model clamp."""
    return min(0.98, max(0.02, accuracy))


def _verdict(mail: ScoredMail) -> str:
    if mail.true_label in {"phishing", "genuine"}:
        return mail.true_label
    return mail.analysis.label


def _verdict_question(mail: ScoredMail, verdict: str) -> QuizQuestion:
    top = next((item.detail for item in mail.analysis.evidence if item.user_visible), None)
    if verdict == "phishing":
        explanation = top or "The labeled class is phishing."
    else:
        explanation = (
            "No strong warning signs. Still confirm unexpected requests for money or credentials "
            "through a separate channel."
        )
    return QuizQuestion(
        id=f"{mail.email_id}:phish_or_legit",
        email_id=mail.email_id,
        kind="phish_or_legit",
        prompt="Is this message phishing or legitimate?",
        subject=mail.subject,
        sender=mail.sender,
        excerpt=_excerpt(mail.observed.body),
        options=[
            QuizOption(id="phishing", text="Phishing"),
            QuizOption(id="genuine", text="Legitimate"),
        ],
        answer_id=verdict,
        explanation=explanation,
    )


def _suspicious_question(mail: ScoredMail, seed: int) -> QuizQuestion | None:
    visible = [item for item in mail.analysis.evidence if item.user_visible and item.contribution > 0]  # noqa: E501
    if not visible:
        return None
    winner = max(visible, key=lambda item: item.contribution)
    options = [QuizOption(id="correct", text=winner.title)]
    for index, text in enumerate(_DISTRACTORS):
        if text == winner.title:
            continue
        options.append(QuizOption(id=f"d{index}", text=text))
        if len(options) == 4:
            break
    _shuffle(options, f"{mail.email_id}:most_suspicious:{seed}")
    return QuizQuestion(
        id=f"{mail.email_id}:most_suspicious",
        email_id=mail.email_id,
        kind="most_suspicious",
        prompt="Which part of this email is the strongest warning sign?",
        subject=mail.subject,
        sender=mail.sender,
        excerpt=_excerpt(mail.observed.body),
        options=options,
        answer_id="correct",
        explanation=winner.detail,
    )


def _link_question(mail: ScoredMail, seed: int) -> QuizQuestion | None:
    for text, href in mail.observed.links:
        real = registrable_domain(host_of(href))
        if not real:
            continue
        options = [QuizOption(id="real", text=real)]
        for visible in re.findall(r"\b((?:[a-z0-9-]+\.)+[a-z]{2,})\b", text, flags=re.IGNORECASE):
            shown = registrable_domain(visible)
            if shown and shown != real:
                options.append(QuizOption(id="shown", text=shown))
                break
        if mail.observed.sender_domain and all(option.text != mail.observed.sender_domain for option in options):  # noqa: E501
            options.append(QuizOption(id="sender", text=mail.observed.sender_domain))
        options.append(QuizOption(id="none", text="The message does not contain a link"))
        trimmed = options[:4]
        _shuffle(trimmed, f"{mail.email_id}:link_destination:{seed}")
        return QuizQuestion(
            id=f"{mail.email_id}:link_destination",
            email_id=mail.email_id,
            kind="link_destination",
            prompt=f"Where does this link really go? It reads: {text.strip()[:180]}",
            subject=mail.subject,
            sender=mail.sender,
            excerpt=_excerpt(mail.observed.body),
            options=trimmed,
            answer_id="real",
            explanation=f"The link text is not the destination. The address goes to {real}.",
        )
    return None


def _shuffle(options: list[QuizOption], key: str) -> None:
    random.Random(_stable(key)).shuffle(options)


def _stable(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


def _excerpt(body: str) -> str:
    def replace(match: re.Match[str]) -> str:
        url = match.group(0)
        url = re.sub(r"(?i)^https://", "hxxps://", url)
        url = re.sub(r"(?i)^http://", "hxxp://", url)
        return url.replace(".", "[.]")

    text = _URL.sub(replace, body).strip()
    if len(text) <= 420:
        return text
    return text[:417].rstrip() + "..."
