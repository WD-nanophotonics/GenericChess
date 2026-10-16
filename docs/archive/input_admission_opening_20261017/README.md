# Input admission and opening-win evidence

`evidence.zip` contains 288 current source files under `source/` and explicit
project-only source/data under `study/`. `manifest.json` lists every SHA256;
`publication-restoration.json` distinguishes execution, repairs and limitations.
No binaries, caches, raw Slack/account records, credentials or logs are included.

Extract to a new directory. From `source/`, use a Python environment with the
project dependencies and a supported Zig compiler to run
`python scripts/build_native_zig.py`, then `python ../study/reader.py`.
The reader disables Python/Native search; it verifies complete state/history and
recorded child receipts. It does not regenerate rules, train, authenticate old
clocks, infer balanced games or independently prove WDL.

`study/inputs.py` is the corrected **research-only** helper. The old max-only and
intermediate effect-guard sources remain named separately. This archive does not
activate a production bridge or fallback. Producer programs use exclusive output
creation; never run them over original frozen results. Portable publication
adapters change only private evidence locations. See the report for original
harness failures and precise source-validation tiers.
