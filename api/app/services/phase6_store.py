"""In-memory datasets for the command center, intelligence, and academy."""

from __future__ import annotations

import csv
import threading
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from layersight.phase6.aggregate import brand_rows, check_domain, domain_report
from layersight.phase6.assess import analyze_observation
from layersight.phase6.models import (
    AnswerIn,
    CommandCenter,
    DomainReport,
    QuizGrade,
    QuizQuestionView,
    SimilarityView,
    UserLayerUpdate,
)
from layersight.phase6.outlook import Defense, command_center, load_pair
from layersight.phase6.quiz import generate, grade
from layersight.phase6.read import read_message
from layersight.phase6.records import ScoredMail

_ROOT = Path(__file__).resolve().parents[3]


@dataclass
class Dataset:
    id: str
    name: str
    mails: list[ScoredMail]
    before: Defense
    trained: Defense
    user_catch_rate: float | None = None
    attempts: list[QuizGrade] = field(default_factory=list)


class Phase6Store:
    def __init__(self, root: Path | None = None) -> None:
        self._lock = threading.Lock()
        base = root or _ROOT
        before, trained = load_pair(base / "data" / "dev" / "configs")
        dev = self._load_dev(base, before, trained)
        empty = Dataset(
            id="empty", name="Empty workspace", mails=[], before=before, trained=trained
        )
        self._datasets = {dev.id: dev, empty.id: empty}
        self._persisted: dict[str, Dataset] = {}

    def list_datasets(self) -> list[dict[str, object]]:
        return [
            {"id": item.id, "name": item.name, "email_count": len(item.mails)}
            for item in self._datasets.values()
        ]

    def get(self, dataset_id: str) -> Dataset | None:
        return self._datasets.get(dataset_id)

    def resolve(self, dataset_id: str) -> Dataset | None:
        found = self._datasets.get(dataset_id)
        if found is not None:
            return found
        cached = self._persisted.get(dataset_id)
        if cached is not None:
            return cached
        loaded = _load_persisted(dataset_id)
        if loaded is None:
            return None
        with self._lock:
            existing = self._persisted.get(dataset_id)
            if existing is not None:
                return existing
            self._persisted[dataset_id] = loaded
            return loaded

    def command(self, dataset_id: str) -> CommandCenter | None:
        dataset = self.get(dataset_id)
        if dataset is None:
            return None
        with self._lock:
            rate = dataset.user_catch_rate
        report = command_center(
            dataset.id,
            dataset.name,
            dataset.mails,
            dataset.before,
            dataset.trained,
            rate,
        )
        brands = brand_rows(
            domain_report(dataset.id, dataset.mails, list(dataset.before.org_domains))
        )
        return report.model_copy(update={"brands": brands})

    def domains(self, dataset_id: str) -> DomainReport | None:
        dataset = self.resolve(dataset_id)
        if dataset is None:
            return None
        return domain_report(dataset.id, dataset.mails, list(dataset.before.org_domains))

    def similarity(self, candidate: str, org_domains: list[str] | None = None) -> SimilarityView:
        extra = list(org_domains or [])
        dev = self.get("dev")
        if dev is not None:
            extra.extend(dev.before.org_domains)
        return check_domain(candidate, extra)

    def questions(self, dataset_id: str, n: int, seed: int) -> list[QuizQuestionView] | None:
        dataset = self.resolve(dataset_id)
        if dataset is None:
            return None
        full = generate(dataset.mails, n=n, seed=seed)
        return [
            QuizQuestionView(**item.model_dump(exclude={"answer_id", "explanation"}))
            for item in full
        ]

    def grade(
        self,
        dataset_id: str,
        answers: list[AnswerIn],
        n: int,
        seed: int,
        record: bool,
    ) -> QuizGrade | None:
        dataset = self.resolve(dataset_id)
        if dataset is None:
            return None
        result = grade(dataset_id, dataset.mails, answers, n=n, seed=seed, record=record)
        if record:
            with self._lock:
                dataset.attempts.append(result)
        return result

    def apply_user_layer(self, dataset_id: str, reset: bool) -> UserLayerUpdate | None:
        dataset = self.resolve(dataset_id)
        if dataset is None:
            return None
        with self._lock:
            if reset:
                dataset.user_catch_rate = None
                return UserLayerUpdate(
                    dataset_id=dataset_id,
                    catch_rate=None,
                    source="config",
                    accuracy=None,
                    reset=True,
                )
            if not dataset.attempts:
                return UserLayerUpdate(
                    dataset_id=dataset_id,
                    catch_rate=None,
                    source="config",
                    accuracy=None,
                    reset=False,
                )
            latest = dataset.attempts[-1]
            dataset.user_catch_rate = latest.catch_rate
            return UserLayerUpdate(
                dataset_id=dataset_id,
                catch_rate=latest.catch_rate,
                source="quiz",
                accuracy=latest.accuracy,
                reset=False,
            )

    def _load_dev(self, root: Path, before: Defense, trained: Defense) -> Dataset:
        folder = root / "data" / "dev" / "emails"
        labels = _labels(root / "data" / "dev" / "labels.csv")
        mails: list[ScoredMail] = []
        if folder.is_dir():
            for path in sorted(folder.glob("*.eml")):
                raw = path.read_text(encoding="utf-8", errors="replace")
                observed = read_message(raw)
                analysis = analyze_observation(
                    observed,
                    path.stem,
                    list(before.org_domains),
                )
                sender = observed.sender_display
                if observed.sender_address:
                    sender = f"{sender} <{observed.sender_address}>".strip()
                mails.append(
                    ScoredMail(
                        email_id=path.stem,
                        subject=observed.subject,
                        sender=sender,
                        true_label=labels.get(path.name),
                        analysis=analysis,
                        observed=observed,
                    )
                )
        return Dataset(
            id="dev",
            name="Development corpus",
            mails=mails,
            before=before,
            trained=trained,
        )


def _load_persisted(dataset_id: str) -> Dataset | None:
    from sqlalchemy import select

    from app.db import Analysis, Email
    from app.db import Dataset as DbDataset
    from app.db import session as open_session
    from layersight.models import Bundle
    from layersight.phase6.outlook import load_pair
    from layersight.phase6.read import read_message

    db = next(open_session())
    try:
        row = db.get(DbDataset, dataset_id)
        if row is None:
            return None
        joined = db.execute(
            select(Email, Analysis)
            .join(Analysis, Analysis.email_id == Email.id)
            .where(Email.dataset_id == dataset_id)
        ).all()
        before, trained = load_pair(_ROOT / "data" / "test" / "configs")
        mails: list[ScoredMail] = []
        for email, analysis_row in joined:
            bundle = Bundle.model_validate_json(analysis_row.payload)
            observed = read_message(email.raw_text)
            sender = bundle.presentation.sender.display_name
            if bundle.presentation.sender.address:
                sender = f"{sender} <{bundle.presentation.sender.address}>".strip()
            mails.append(
                ScoredMail(
                    email_id=email.id,
                    subject=bundle.presentation.subject or email.filename,
                    sender=sender,
                    true_label=email.ground_truth,
                    analysis=bundle.analysis,
                    observed=observed,
                )
            )
        return Dataset(
            id=row.id,
            name=row.name,
            mails=mails,
            before=before,
            trained=trained,
        )
    finally:
        db.close()


def _labels(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    found: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            filename = (row.get("filename") or "").strip()
            label = (row.get("label") or "").strip()
            if filename and label in {"phishing", "genuine"}:
                found[filename] = label
    return found


@lru_cache(maxsize=1)
def get_store() -> Phase6Store:
    return Phase6Store()
