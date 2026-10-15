# Frozen checked-PV evidence

`evidence.zip` contains technical sources, frozen plans, rules, full result rows,
cost/failure logs and a historical source-only qualification export. `manifest.json`
maps each member to its restoration path and original/public SHA256. Machine/user
paths are sanitized only in publication copies; binaries, raw Slack and XML machine
metadata are excluded. Verify archive/member hashes and CRC before use.

From the repository, with installed Python312, pytest and Zig:

```powershell
.\.venv\Scripts\python.exe docs/archive/checked_pv_20261015/replay_public.py --zig .venv/Lib/site-packages/ziglang/zig.exe
```

The entry creates a NEW ignored replay workspace, restores only manifest paths,
builds the historicalV1/V2 images, runs52API checks,35root/4497action/two-goal
qualification and the frozen96query full-history replay. It does not overwrite
the active checkout, rerun paid timing curves or import older private files.
Existing Windows/Python/Zig dependencies are used; no installer guarantee.

The historical source export predates065eff0d's automatic-PENDING dependency
repair. Its qualified timing rows are not measurements of that later image.
Current product behavior and2648full-test evidence belong to
`docs/research/SLACK_REVIEW_FIXES_20261015.md` at that fixed revision. Restore the
historical package when replaying its drivers rather than mixing old images with
current capability gates. No product default, generator filter or AUX solver change.

For naive terminal-tail reproduction use `reproduce_injections.py`; the earlier
`injections.py` expected its then-live baseline caller and is retained as history.
`analyze_q32.py` derives the reported table from frozen rows without new searches.
Full resource/generation drivers preserve their original output names: run them
only in a fresh restored workspace and under the original frozen limits if needed;
do not overwrite the published records or interpret a timing rerun as the original.

Report: `docs/research/CHECKED_PV_REPLAY_AND_WIDE_PREPARATION.md`.

Late correction: frozen `exact_generic_preference_solver_v3.py` is a board-action
reference and must not certify declaration games. Current source adds explicit
unsupported-domain refusal after PRIMARY reproduced AUX's counterexample. The
Native/caller curves and qualification above do not invoke that reference.
