# GenericChess F92 wheel artifact acceptance closeout

## Artifact

- Filename: `generic_chess-0.8.0a9-cp312-cp312-win_amd64.whl`
- SHA-256: `bf7756200e7e8f515dd6ec638b403858eb942349f86d577b46cc37bfe7e0d9ac`
- Built from the F92 candidate checkout with `pip wheel . --no-deps
  --no-build-isolation -w <temporary-dist-dir>`.

The initial ZIP audit found that setuptools did not include the localization
JSON resources. F92 corrected this with explicit
`tool.setuptools.package-data` for `generic_chess = ["ui/i18n/*.json"]`; the
artifact above is the rebuilt wheel after that correction.

## Acceptance evidence

- ZIP contents include `generic_chess/__init__.py`, the UI package, all three
  localization files (`en.json`, `zh_CN.json`, `ja_JP.json`), `.dist-info/METADATA`,
  and `.dist-info/entry_points.txt`.
- `METADATA` reports `Name: generic-chess` and `Version: 0.8.0a9`.
- `entry_points.txt` retains
  `generic-chess-ui = generic_chess.ui.app:main`.
- The wheel was installed with `pip install --no-deps --target <temporary-target>
  <wheel>` and imported from that target with the repository root absent from
  the subprocess working directory.
- Wheel-installed runtime checks passed: imported `generic_chess.__file__`
  was inside the temporary target; metadata matched `__version__`; Western
  Chess and Standard Shogi compiled with initial legal-action counts 20 and 30;
  all three localization tables returned a real `app.title`; module
  `--version` returned `0.8.0a9`; and offscreen UI `--smoke` exited 0.

## Verification

`tests/test_f92_wheel_artifact_acceptance.py` reproduces the wheel build, ZIP
audit, non-editable target install, outside-checkout runtime checks, version
entry-point check, and offscreen UI smoke. No installer, PyPI upload, tag,
release, chess semantics, AI/search/evaluator, Arena, training, or Heavy work
was added.
