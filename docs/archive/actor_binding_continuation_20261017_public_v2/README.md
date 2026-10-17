# Publication-copy correction - 2026-10-17

This directory supersedes the older current-tree publication copy. The original
scientific source/results remain pinned at the original Git revision and in
ignored private originals. Only the personal directory strings listed in the new
manifest changed; retained data/source bytes match exactly. Earlier source-byte
identity claims below refer to that original qualification, with the legacy
compatibility path now explicitly excepted. Do not execute external integration
functions. The new source-check qualification is separate from historical runs.
This removes paths from this copy; it DOES NOT purge existing Git history or
claim the whole repository has no personal information. No new model, training,
search, game, default, Core or Native implementation change is made.

## Original reproduction instructions and historical scope

# Actor binding and conditional continuation evidence

`evidence.zip` has separate `frozen_source/` (PUBLIC46293226) and
`current_source/` (corrected Native kernel) trees, plus complete `policy/` and
`native_repair/` source/data. `manifest.json` gives every hash and the archive CRC
was checked. Binaries, caches, logs, raw Slack/account data and credentials are
excluded; no paper full text is copied.

Extract to a new directory. With project Python dependencies and supported Zig,
from `current_source/` run `python scripts/build_native_zig.py`, then
`python ../native_repair/reader.py`, `python ../native_repair/full_session.py`
and `python ../policy/reader.py`. The policy reader disables search and uses
complete actual records, histories and PV continuations. Rebuild/use
`frozen_source/` separately to retain the original execution tier; do not call
current code a rerun of its wall clocks, search decisions or games.

Producer scripts use exclusive result creation and must not overwrite frozen
results. Portable adapters only replace private evidence locations. The Native
repair keeps conservative provider exclusions and rejects affected older kernels
without the new capability; it does not activate a new model/default/fallback or
qualify DEV_AUX's v5. The sampling groups are observations, not full-history
state equivalence. See the purpose report for actual UNKNOWN, exact means,
exposure/correlation, source failures and qualification tiers.
