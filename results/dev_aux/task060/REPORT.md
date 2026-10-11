# Task060: protected full-q4 recorded completion

At primary revision bebe3d98ebb0832207e112ca0755fa9837cef3e7, all 56 archive members and 104 caller rows verify. The declaration/producer raw hashes and the exact generated function hash bind to baseline d4a588fe50a5f90c0ad5026f28f02905ee86ed65. This is independent record/source validation; no primary searches were rerun.

|Scope|Calls / pairs|Refresh completes / aborts|Depth losses|Action and score changes|Returned q0 to q4|
|---|---:|---:|---:|---:|---:|
|Builtin Native legality|48 / 24|20 / 4|0|8|8|
|Builtin Core|40 / 20|14 / 6|0|8|8|
|Generated13/15, both routes|16 / 8|8 / 0|0|0|2|

Exact declared coverage is checked, including Core ChessEP only 1/4 seconds, both orders, and generated roots only 4 seconds. Every corresponding decision/stat field agrees. Actual Native calls are positive exactly in Native rows; no fallback/operational failures are recorded. All push/pop counters balance and producers assert full Runtime identity/history restoration. The event logger itself checks only position/ply/terminal plus balanced depth: it is not the full history witness. The stronger post-call producer snapshot contains identity/hash/history/occurrences/aliases.

All ten aborted refreshes keep reserve action, score, PV, completed D1 and returned ordinary-q0. The metadata source is `main_iteration`, not a separate reserve-source enum. Every refresh reuses the same budget object/deadline and cumulative node/q counters. The source creates the budget before history import; refresh does not reset it, and TT is disabled/cleared for refresh then caller configuration restored in finally. This source-plus-record evidence is not independent execution of all abort/cancellation paths. TT and scheduling jointly change; it is not a pure q-overhead experiment.

Sixteen builtin pairs change action/score: ChessEP 1s (106 to17), Shogi-middle Native1s/Core1/4s (1222 to6), and Shogi-drop Native16/64s/Core64s (748 to946), each in both orders. These are changed decisions with matched within-pair weighted evaluation, not strength/WDL evidence. The two generated q upgrades preserve the same score4228/action; q metadata alone is not decision benefit. No completed-depth loss across five exposed roots proves no such loss elsewhere or with warm tables.

Successful refresh visits are 162 (ChessEP),251 (Shogi-middle),12908 (drop). Measured same-clock stage durations remain meaningful; setup/reserve and deeper incomplete work remain in cumulative caller totals. 104 rows total 1,783.322 recorded caller seconds; totals match primary's report. These are historical same-machine observations under ordinary parallel load, not a new controlled speedup.

## Clock interpretation correction

The logger uses perf_counter for event `at`, while the deadline originates from monotonic. The current auxiliary Python3.12.14 Windows runtime reports QPC/0.1us and GetTickCount64/15.625ms respectively. Immediate current samples differ by about25ms. Current offsets do not reconstruct historical offsets. Therefore the auditor retains `deadline - at` only as `cross_clock_difference_unqualified`, never exact slack or proof a completed refresh exceeded its budget. Same-budget/deadline identity, monotonic budget checks and perf-to-perf durations are unaffected. The retained Core16s drop abort is valid from phase/result records and same-clock costs; precise cross-clock remaining milliseconds are not established. A future diagnostic can log budget-clock event time alongside the performance duration clock. This is an evidence-format observation, not a requested product/timing-rule change or automatic rerun.

Dot independently read the fixed source and official Python clock contract, and agreed with the scope correction. Its complete response was saved and reconciled with exact request readback before adoption; it did not rerun104 calls or inspect this machine. No routine acknowledgement or old-cohort rerun followed. The clock references have undefined origins, with guaranteed differences within each clock, per [Python3.12 time documentation](https://docs.python.org/3.12/library/time.html#time.monotonic) and [perf_counter documentation](https://docs.python.org/3.12/library/time.html#time.perf_counter). Current runtime evidence is explicitly auxiliary-local, not historical clock attestation. Binary hashes establish runtime identity, not a C-source build certificate. Generated13/15 are previously exposed profiles, not fresh holdouts; builtin and generated evaluation families are not silently equated. Default/UI behavior remains untouched.

`analyze.py` reproduces all archive/coverage/row/source checks using fixed Git objects. `AUDIT_NOTES.md` retains the initial auditor source-label assumption error. `clock_boundary.json` records current clock implementation and sampling scope.
