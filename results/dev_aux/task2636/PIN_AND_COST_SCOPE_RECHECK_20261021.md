# task2636 frozen-pin and cost-scope recheck — 2026-10-21

## Frozen-source check

Read-only SHA-256 recheck passed for the actual frozen design
`one-init-study-plan.json`
(`a3af462f9db4018118619aea9d79374e7e876f83735559d8269a80b506c73c40`),
`partial_evaluation_audit.py`
(`e894da78fd22d06771419fb4003685fff6df5413ea59725d2321ed81399ef8ca`), its
focused tests
(`f5471b1049d49701b56fbb99ee669af5b71a8e5c642f2a4193bf6677cecf3fa9`), the
evaluation-budget v2 audit source
(`9e7a11cdfa684a22fcdfd2004adddc8e24350a93c378e76fc10a2cf8dce4c30b`), its
saved receipt
(`4ebe74f14004ceb876c5b405ab08116b5a79d7c5a4ad8bb8541ec2161b6831ca`), and the
estimate receipt verifier
(`1be5cb9b9ff69468f0f9e0e3d77687330347109e428dd7245e175b4493dc377a`) and saved
receipt
(`749555e0b159f7c17a604f1ce7b8cb377df9c85271cf8753ef11b43902a6f6a0`).
The plan still declares 6,600 cumulative process-wall seconds, with 1,200
preparation/audit/reporting, 2,400 training, and 3,000 evaluation seconds.
`run-v1` and its registration are absent. The evaluation node-limit finding
remains verified; per-query seconds enforcement remains unverified because no
task2636 runner exists.
Read-only write-helper check found no existing durability guarantee to reuse.
`generic_chess/learning/arena.py` at SHA-256
`2bf24e7b6f136df0f2ad450e6ed9e19935284671ffce4072e9f82a3095756e03` writes a
temporary JSON file and replaces the destination, but does not flush/fsync it.
The pinned task2625 training/evaluation sources (SHA-256
`12d864caf62f5be604b49a3a6d340defd91c13e43804ecae179a7e56f3c98ea1` and
`37da34de1cb2b00778510d384196d66efa307c23473b87a1d3f1a1dd69bdbcc6`) flush
JSONL handles after query and episode/slot records, but do not fsync (task2625/train.py lines 194–195 and 220–221; task2625/evaluate.py
lines 172–173 and 190–191). The helper is lines 855–862. These
sources are valid format/control-flow precedents, not proof of crash-durable
stop receipts. A candidate-index lifecycle needs an explicit durability
boundary and interruption tests; this adds to the unpriced work.

An initial manual SHA spot-check compared the expected frozen-design hash to
`plan.json` and the verifier hash to `audit_estimate_basis_branching.py`.
Those were the wrong files: `plan.json` is the earlier exact-history inventory
plan, and the hash belongs to `verify_estimate_basis_receipts.py`. Rechecking
the designated files above found no frozen-source drift. Re-running the two
write-once audit scripts correctly refused to overwrite their existing receipts;
their saved receipts and source hashes were checked directly instead.

## Cost interpretation

At the 00:06:34Z session checkpoint, the active segment had 3,313.414
confirmed effective research seconds. The earlier 640.816 seconds is already
inside that cumulative segment total: its source says the same ledger rose from
2,074.555 to 2,715.371 seconds, so adding it again is a double count. The
plan's 542.632-second prior preparation charge is itself a mixed budget
allocation: 227.998s observed inventory plus 4.762s observed prefix audit,
165.872s projected root-pool preparation, and 144s projected full-source audit.
It is not a single measured duration. Combining that allocation and the
2,801.988-second projected training/evaluation with the 3,313.414 confirmed
Agent-work seconds yields a known mixed-cost scenario of 6,658.034 seconds,
58.034 above 6,600. This mixes effective Agent work and a projected process
allowance; it is not measured cumulative process-wall runtime or evidence that
a registered experiment hit its cap. The plan's cap unit is cumulative process
wall time; no task2636 process was registered or started.

The 1,200-second preparation/audit/reporting allocation cannot be shown to
cover the recorded work plus the still-unpriced candidate runner, integrated
audit, terminal fixture, stop-safe lifecycle tests, and reporting if those
costs are assigned to the frozen study. The missing implementation/validation
estimate could change the mixed-cost total materially. Do not register or
launch on the inherited 66.70-minute projection. Do not change frozen inputs
or caps. Future accounting must keep Agent effort, measured process time, and
projections separate, avoid double-counting cumulative intervals, and close
the remaining implementation estimate.

## Decision

No source-drift blocker was found. task2636 remains design-only and not
executable within a demonstrated all-in cost envelope; preserve its unregistered
state. This recheck changes no registration, plan, input, run result, or cap.
