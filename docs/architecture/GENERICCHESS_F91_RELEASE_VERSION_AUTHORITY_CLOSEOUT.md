# GenericChess F91 release version authority closeout

## Decision

`generic_chess.__version__` is the single release-version authority. Setuptools
reads it through `tool.setuptools.dynamic`, so distribution metadata, runtime
imports, Qt application metadata, MainWindow About/diagnostics, and the two UI
entry points all expose the same value.

The UI supports `--version` for both `python -m generic_chess.ui` and the
declared `generic-chess-ui = generic_chess.ui.app:main` console script. Existing
smoke, snapshot, and ruleset arguments remain unchanged.

## Evidence

- `tests/test_f91_release_version_authority.py` verifies dynamic setuptools
  binding, installed metadata, QApplication metadata, About text, module and
  generated console entry points, and the stable console declaration.
- No installer, PyPI, tag, chess-semantics, AI/search, evaluator, Arena,
  training, or Heavy behavior was changed.
