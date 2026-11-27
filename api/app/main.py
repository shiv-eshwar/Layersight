"""HTTP API. Health and assumptions stay available with no database. Dataset routes open one on first use."""

from pathlib import Path

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from app.settings import Settings
from layersight import __version__
from layersight.refs import weights

settings = Settings()
_ROOT = Path(__file__).resolve().parents[2]
_ASSUMPTIONS = _ROOT / "engine" / "layersight" / "config" / "assumptions.yaml"

app = FastAPI(
    title="LayerSight API",
    version=__version__,
    summary="Phishing triage and layered-defense simulation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)

app.include_router(router)


def _assumptions() -> dict[str, object]:
    if not _ASSUMPTIONS.is_file():
        return {}
    loaded = yaml.safe_load(_ASSUMPTIONS.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine_version": __version__}


@app.get("/api/v1/meta")
def meta() -> dict[str, object]:
    return {
        "engine_version": __version__,
        "contract_version": "1",
        "weights_hash": weights().digest,
        "assumptions": _assumptions(),
    }
