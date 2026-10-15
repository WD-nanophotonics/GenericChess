# Checked reply reuse and first-source lookup evidence

`evidence.zip` and `manifest.json` preserve technical source snapshots, complete
plans/rows/missing slots/censors, failures, same-input controls and original/public
SHA256s. Publication copies sanitize machine/account information; original private
records remain local. No binaries or raw Slack/account records.

Run from repository root with the existing Windows/Python3.12/Zig environment:

```powershell
.\.venv\Scripts\python.exe docs/archive/reply_witness_20261015/replay.py
```

It verifies all archive hashes, restores a unique ignored local source export,
rebuilds the prepared combinedV1 and optional replyV2 images, runs38focused checks
and35roots/4497legal actions with full PV SHA/actor/check histories. An audit hook
rejects older private input reads. This is source qualification on the existing
machine toolchain, not a clean-machine installer or timing-study replication.
Actual sanitized-copy replay passed38focused/35roots4497actions in46.846s;
publication-replay.json records that execution. Final product C sources match
the export exactly.

`frozen_export/` is the self-contained source qualification tree. `evidence/`
retains each actual baseline/hint/counter-free/dense/combined/fault/probe source
variant and its plan/output. `support/` retains the exact already-paid rules and
inputs used by historical drivers; timing reruns must rebuild the matching image
names and providers, never use the changed installed product as a baseline.
Original helper imports also expected an older wide provider; source-only replay
avoids that dependency entirely. No all-domain equivalence/strength claim.
