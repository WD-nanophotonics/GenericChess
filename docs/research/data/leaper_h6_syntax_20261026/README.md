# Pure H6 syntax/legality study, PRIMARY, 2026-10-26

Research evidence, not an activated backend. See ../../LEAPER_H6_SYNTAX_20261026.md.

`manifest.json` binds every gzip and decoded byte stream. `records.json.gz` and
`executed-sources.json.gz` map names to exact UTF-8 source bytes (the `utf8` value),
byte count and SHA256; encoding that value as UTF-8 reconstructs the saved file.
Six query archives retain all 1520 raw returns, including abort/recovery outcomes.
The final v4 experimental C bodies are retained; full earlier v1/v2/v3 source
bodies were not preserved as originals. Failure receipts and v2 hashes remain.
A zero-query Python import-launch failure remains private because its traceback
contains a personal absolute path; it was `ModuleNotFoundError: scripts`, fixed
by invoking the own script through runpy from the repository root, before Core.

Base source: `193dad1668c00cb573349136c5c557bd5c2a87e6`. The three C source copies
replace those files in an isolated build only; all other C/H byte hashes are in
`isolated-native-build-plan.json`. Never overwrite an installed pyd by replaying.
The build uses Python3.12/Windows AMD64/Zig with `-O2`; binaries are not published.
Own executed scripts retain their original relative `.local_agent/h6-study-c7cb630b`
paths, so they are source capsules, not an automatic work request or one-click
rerun. Their local stop/config readers remain active. Reproduction needs a new
explicit bounded plan and outputs; do not overwrite frozen files or role state.

Published AUX data is consumed as DATA only, pinned to
`5584387c8de5b23a3b1524cce9c29bd694bee2d8`, under
`docs/research/data/leaper_h6_initial_truth_20261023/`. Source file hashes are in
`fixed-source-bindings.json` / `closed-domain-sources.json` inside records.
The20 full RuleSets/records/state hashes/source child labels are in
`literal-qualification-result.json`; no archived AUX solver was executed.

Derivative qualification drivers retain a final20-root installed/private-provider
comparison and a100-repeat provider timing tail from the original qualification.
For binding/syntax/installed variants, the all18340position binding comparison is
the variant qualification. The inherited timing tail is NOT that variant's
microbenchmark and is excluded from the cost conclusions. Native direct refusal
rows are similarly separate from full-position binding comparisons.

Per-arm query timing starts at Player/provider construction and ends before raw
record write. Outer batch time additionally includes shared compile/replay/
validation/writes; it is not allocated by arm. Imports, engineering, builds and
publication are not amortized away. No heldout/class-wide/strength claim follows.
