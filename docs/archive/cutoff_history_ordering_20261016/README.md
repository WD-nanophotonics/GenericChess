# Exact-action history source/evidence —2026-10-16 JST

`evidence.zip` contains620technical members, exact full rules/root histories,
all planned/censored results and failures, original and final Native variants,
source and experiment/consumer scripts. `manifest.json` records every byte count/
SHA256; `publication-replay.json` records ACTUAL extracted-copy execution.
No Native binaries or account/Slack originals are shipped.

The source snapshot is baseef9d4a39plus the exact guarded NativeC working change;
member hashes bind the contents, while the final Git delivery commit binds the
whole artifact. Product NativeC SHA256:
`1c855ae56e946ec6cb8e57f60a36a18cb75cfec2ee8061047469f3e0bee3fac3`.

For recorded-data replay, extract, build the supported Native extension from
`source/generic_chess/_native` using a compatible Python/Zig environment, then
run from `source`:

```
python -S ../research/consumer.py ../research
python -S ../research/decision_replay.py ../research
```

The consumers assert imports originate in the restored source. They run no
search/training/proof and check1344query/3324PV-edge and12game/258physical-edge
histories and main+q budgets. Actual receipt uses Windows/Python3.12.14/Zig0.16,
not a new machine. Frozen producers preserve their original project-local input
layout; reading them is not a claim the expensive benchmark was independently
rerun. The first unused-diagnostic chess import failure and fixed replay are
explicitly recorded, without rewriting any original search result.

Refer to ../../research/CUTOFF_HISTORY_ORDERING_20261016.md for finite-objective
cost denominators, negative cases, UNKNOWN and actual role-control limits.
