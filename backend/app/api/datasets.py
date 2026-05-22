"""Dataset endpoints — upload, list samples, generate."""
from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from ..config import SAMPLES_DIR
from ..data.generators import generate_grr_samples, generate_spc_samples
from ..services.audit_service import audit

router = APIRouter(prefix="/datasets", tags=["datasets"])

# In-memory dataset store: id -> Path
_datasets: dict[str, Path] = {}


def _preload_samples() -> None:
    if SAMPLES_DIR.exists():
        for f in SAMPLES_DIR.glob("*.csv"):
            _datasets[f.stem] = f


_preload_samples()


@router.get("/samples")
def list_samples() -> dict:
    _preload_samples()
    return {
        "samples": [
            {"id": k, "name": k, "path": str(v)}
            for k, v in _datasets.items()
        ]
    }


@router.post("/upload")
async def upload_dataset(file: UploadFile) -> dict:
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files accepted.")
    tmp = Path(tempfile.mkdtemp()) / (file.filename or "upload.csv")
    with tmp.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)
    try:
        df = pd.read_csv(tmp)
    except Exception as exc:
        raise HTTPException(400, f"Cannot parse CSV: {exc}") from exc

    did = str(uuid.uuid4())
    _datasets[did] = tmp
    audit.log("DATASET_UPLOADED", "Dataset", did, f"Uploaded {file.filename}")
    return {
        "dataset_id": did,
        "filename": file.filename,
        "rows": len(df),
        "columns": list(df.columns),
        "preview": df.head(10).to_dict(orient="records"),
    }


class ScenarioRequest(BaseModel):
    scenario: str


@router.post("/generate/grr")
def generate_grr(req: ScenarioRequest) -> dict:
    valid = {"pass", "marginal", "fail"}
    if req.scenario not in valid:
        raise HTTPException(400, f"scenario must be one of {valid}")
    generate_grr_samples()
    _preload_samples()
    key = f"grr_{req.scenario}"
    audit.log("DATASET_GENERATED", "Dataset", key, f"Generated GRR {req.scenario}")
    return {"dataset_id": key, "scenario": req.scenario}


@router.post("/generate/spc")
def generate_spc(req: ScenarioRequest) -> dict:
    valid = {"stable", "shift", "drift", "anomalies"}
    if req.scenario not in valid:
        raise HTTPException(400, f"scenario must be one of {valid}")
    generate_spc_samples()
    _preload_samples()
    key = f"spc_{req.scenario}"
    audit.log("DATASET_GENERATED", "Dataset", key, f"Generated SPC {req.scenario}")
    return {"dataset_id": key, "scenario": req.scenario}


def get_dataset_df(dataset_id: str) -> pd.DataFrame:
    """Utility used by other routers."""
    _preload_samples()
    if dataset_id not in _datasets:
        raise HTTPException(404, f"Dataset '{dataset_id}' not found.")
    return pd.read_csv(_datasets[dataset_id])
