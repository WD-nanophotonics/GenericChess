"""Run pytest after preloading a specified fresh Native extension."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
native_path = sys.argv[1]
output_path = Path(sys.argv[2])
pytest_args = sys.argv[3:]
spec = importlib.util.spec_from_file_location("generic_chess._native_core", native_path)
if spec is None or spec.loader is None:
    raise RuntimeError(native_path)
module = importlib.util.module_from_spec(spec)
sys.modules["generic_chess._native_core"] = module
spec.loader.exec_module(module)
import pytest  # noqa: E402

buffer = io.StringIO()
with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
    code = pytest.main(pytest_args)
output_path.write_text(buffer.getvalue() + f"\nexit_code={code}\n", encoding="utf-8")
raise SystemExit(code)
