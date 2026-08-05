"""Preview CLI smoke tests (workspace-local temp dir due to sandbox)."""

import os
import shutil
import uuid
from pathlib import Path

import pytest

from generic_chess.visual import preview as preview_mod


@pytest.fixture()
def preview_tmp_dir():
    base = Path(__file__).resolve().parent.parent
    tmp = base / f".gc_prev_tmp_{uuid.uuid4().hex}"
    os.makedirs(tmp, mode=0o777)
    yield tmp
    resolved = tmp.resolve()
    if tmp.exists() and resolved.is_relative_to(base.resolve()):
        shutil.rmtree(resolved)


def test_preview_writes_svgs_and_html(preview_tmp_dir):
    code = preview_mod.main(["--out", str(preview_tmp_dir), "--size", "64", "--seed", "7"])
    assert code == 0
    svgs = list(preview_tmp_dir.glob("*.svg"))
    assert len(svgs) >= 20
    assert (preview_tmp_dir / "king_w.svg").exists()
    assert (preview_tmp_dir / "pawn_b.svg").exists()
    assert (preview_tmp_dir / "index.html").exists()
    for path in svgs + [preview_tmp_dir / "index.html"]:
        assert path.read_text(encoding="utf-8").strip()


def test_preview_no_html_flag(preview_tmp_dir):
    code = preview_mod.main(["--out", str(preview_tmp_dir), "--no-html"])
    assert code == 0
    assert not (preview_tmp_dir / "index.html").exists()


def test_preview_out_must_be_directory(preview_tmp_dir):
    blocker = preview_tmp_dir / "file.txt"
    blocker.write_text("x", encoding="utf-8")
    assert preview_mod.main(["--out", str(blocker)]) != 0


def test_preview_includes_random_ruleset_types(preview_tmp_dir):
    code = preview_mod.main(["--out", str(preview_tmp_dir), "--seed", "42", "--size", "48"])
    assert code == 0
    rand_files = [p.name for p in preview_tmp_dir.glob("rand_*.svg")]
    assert len(rand_files) >= 10
