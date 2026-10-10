"""Stable local-service identity without GUI or server dependencies."""
import hashlib
import os
from pathlib import Path

APPLICATION = "generic-chess-web"
ROOT = Path(__file__).resolve().parents[3]


def instance_id(state_dir):
    paths = [os.path.normcase(str(path.resolve())) for path in (ROOT, Path(state_dir))]
    return hashlib.sha256("\0".join(paths).encode("utf-8")).hexdigest()
