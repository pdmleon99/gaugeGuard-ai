"""App configuration from environment."""
from __future__ import annotations

import os
from pathlib import Path

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./gaugeGuard.db")
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
DEMO_MODE: bool = os.getenv("DEMO_MODE", "true").lower() == "true"

# DATA_ROOT can be overridden via env var for Docker/cloud deployments.
# Default: walk up from this file to find the gaugeGuard project root.
_default_data_root = Path(__file__).parent.parent.parent.parent / "data"
DATA_ROOT: Path = Path(os.getenv("GAUGEDATA_DIR", str(_default_data_root)))

DATA_DIR: Path    = DATA_ROOT
SAMPLES_DIR: Path = DATA_ROOT / "samples"
