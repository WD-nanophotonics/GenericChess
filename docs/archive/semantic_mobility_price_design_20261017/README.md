# Semantic mobility and price-design evidence

The companion report is ../../research/SEMANTIC_MOBILITY_AND_PRICE_DESIGN_20261017.md.
manifest.json lists every payload with private-original and publication-copy hashes.
The ZIP has446 members, including122 source/support/config files, CRC and all member
hashes checked. Only actual local user paths are redacted in outgoing copies.
Exact originals stay ignored; scientific data are not excluded by origin.

## Contents and limits

- `source/`:120 unchanged existing Python/test files plus a source-isolating launcher
  and minimal pytest configuration. No learning/UI/benchmark, Native C/binary,
  account data or personal bridge defaults. This is a qualified Core closure,
  not a complete repository export or independent rule implementation.
- `recorded/`:frozen plans/rules/profiles, all branch/state/decision/game records,
  corrections/invalid attempts, private source prototypes, cap failures and readers.
  The recorded producer scripts are provenance, not instructions to run more games.
- `recorded/consumer-v1-invalid-status/`:ALL48 invalid one-ply attempts. They are
  ongoing states, not draws. The corrected48NP games are separate.
- `recorded/fresh-transfer/`:original36 completed cells and three wrong-compiler
  failures. `missing-atom-repair/` contains ONLY12 formerly unstarted cells using
  the existing correct adapter, under the SAME original1800s clock. Joint data
  are48 cells/2254plies, not84 games or a new selected seed sample.
- `recorded/bulk-attack/`:private clear-ray prototype16calls/eight equal-work pairs;
  median.962 misses.90 and retains adverse cases. It is NOT activated source.
- Old public240s and scalar-file180s readers remain partial. `runtime-reader-v3-`
  qualification/result records the distinct successful96game/2802fullstate/4543PV
  source replay, not a relabelled old run. The90s root-scan probe remains partial;
  its recorder-only fix is unexecuted. Do not call all planned calls complete.

## Fresh disposable reproduction

Use a NEW empty directory for each reproduction. NEVER overlay a live checkout,
its `.local_agent`, user stops, archives or producer outputs. Extract the ZIP in a
separate archive directory and copy `source/*` into the new WORK directory. Keep
`recorded/` immutable outside WORK. A Python environment with pytest is sufficient;
no Native build or scientific worker is required for these read-only checks.

Inside WORK create `.local_agent/price-measure-20261017` as DATA. Copy ONLY these
recorded inputs/readers to the matching relative paths below DATA:

1. `inputs.json`, all16 `slot-*.json`, `reader.py` and `runtime-reader.py`.
2. `consumer-inputs.json`, all48 `consumer-game-*.json`, and the48 game files under
   `consumer-v1-invalid-status/` (needed only to verify the invalid-label finding).
3. `fresh-transfer/consumer-inputs.json`, its36 game files, and
   `fresh-transfer/missing-atom-repair/consumer-inputs.json` plus12 game files.

Do NOT copy old `reader-result`, runtime progress/result or stop files into DATA.
The archived results remain the comparison tier. ONLY in the new disposable WORK,
create `.local_agent/rollout.json`, `advisor.json`, `slack.json` with
`{"stopped":false,"user_paused":false,"scope":"disposable reproduction"}`.
Those are local test fixtures, never authority to clear a live user stop.

Run from WORK:

```text
python qualify-source.py
python qualify-source.py --reader
python qualify-source.py --runtime-reader
```

The launcher excludes the host's project editable finder in this process only,
asserts Native is absent and all project modules come from WORK. The first attempt
without that isolation found normalNative; its59PASS is NOT pure-source proof.
Expected pure-source tests:53PASS/6explicitNative skips. Expected first reader:
303 finiteD2 values,11366 complete replies and48 invalid original labels. Expected
v3 runtime reader:96records,2802 full public GameState/action comparisons,
4543 legal PV edges,73 actual terminals/23administrativeUNKNOWN. Each version has
its own recorded cap/source tier. V3 checks persistent stop files at complete Core
boundaries and deadlines internally; pulse/per-scalar/realtime equivalence is not
claimed. Fresh-run clocks are new observations, never replacement historical data.

These commands do NOT rerun policy games, price search, training, a prover or old
performance clocks. The optional producer files can be inspected with their plans;
executing them is a new experiment and needs separate output locations. Failed
syntax fragments and original capped readers are deliberately retained, not an
instruction to execute every `.py` file indiscriminately.

The separate root-startup-contract plan/results add10 cold existing-flag calls on3 timed failures and2 actual win controls. They do not complete the capped all-reply study or activate a new default.
