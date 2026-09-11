# GenericChess F86Q bounded checking-forcing depth-3 probe

Status: complete. F86Q is a specialized three-ply local proof over only the
pre-move states observed while replaying the 12 frozen F86O games. It creates
zero new games, does not change a ruleset or tape, and does not run generic
search, AlphaBeta, BFS, training, teacher, F85, or Heavy compute.

## PREP authority

F86Q PREP was published at commit
`dbecdc16376a70654160930e2205a01bcae37e34`. Its manifest is
`artifacts/f86q_check_forcing_depth3_probe/manifest.json`, Git blob
`76e15ba9320ab490d5d6321852eb5b683b6002fb`. The runner blob at PREP is
`52b9191c661573c72cac5f0de216e37e94fabfb8`; RESULT does not modify it.

The PREP freezes the F86O manifest authority
`artifacts/f86o_common_tape_triarm_dynamic_smoke/manifest.json` at blob
`1d16cf69a7ce5f7347352162dcbd351485ee8c5af`, its RESULT at blob
`fccfffdb5ec8c3e72eeb78f4bb73c8244ca2e322`, all six ruleset fingerprints,
the four 32-value PolicyTapes, and all 12 F86O action-sequence and final
position digests. The F86P-R1 baseline is
`e0aa2d7c606b395402ec252c5688a51c8eac2c2a`.

State selection is deterministic: replay every F86O trajectory with the
frozen canonical action ordering and select each pre-move occurrence with at
least one corrected checking successor, where checking means
`is_in_check(child.position, child.position.side_to_move, compiled)`. Unique
roots are deduplicated by `(ruleset_fingerprint, position_identity_key)` while
trajectory occurrence multiplicity remains in RESULT. The F86H/F86P
cross-ruleset geometry surrogate is absent from this probe.

## Fixed forcing proof

For every selected root and every legal checking action, F86Q enumerates the
opponent's legal replies and then the original attacker's legal continuations
after each reply. This is exactly three plies from root to attacker
continuation; no fourth layer is expanded and no evaluation search is used.
The new-successor count includes opponent-reply and attacker-continuation
successors, without double-counting the replay's root successors. The hard
cap is 8,192 and truncation would route to
`CHECK_FORCING_VALUE_UNRESOLVED_DUE_TO_PROBE_CAP`.

Classifications are exact:

- `MATE_IN_ONE`: the checking child is checkmate and the root actor wins.
- `FORCED_MATE_IN_TWO`: every legal opponent reply has an attacker mate-in-one.
- `FORCED_CHECK_CONTINUATION`: not forced mate in two, and every opponent reply has an attacker checking action.
- `ESCAPABLE_CHECK`: at least one opponent reply has neither continuation.

Each action record retains the root digest, action digest, occurrence count,
opponent reply count, minimum/maximum attacker continuation counts, replies
with mate/check continuations, classification, and whether the frozen tape
selected it at each occurrence.

## RESULT

The RESULT replay completed with 12/12 action-sequence and final-position
matches, zero new games, and 1,268 specialized successor probes against the
8,192 cap. Truncation was false. The exact focused suite passed 6 tests.

| Arm/sample | Root occurrences | Unique roots | Unique checking actions | Occurrence classifications | Tape-chosen classifications | Opponent reply distribution |
| --- | ---: | ---: | ---: | --- | --- | --- |
| L / V4-3 | 0 | 0 | 0 | — | — | — |
| L / V5-3 | 7 | 4 | 4 | ESC 4 / 4 | ESC 1 | 2:4 |
| F / V4-3 | 7 | 7 | 7 | ESC 7 / 7 | ESC 1 | 2:2, 3:5 |
| F / V5-3 | 25 | 22 | 38 | ESC 22 / 23; FCC 15 / 18; FM2 1 / 1 | ESC 3; FCC 1 | 1:15, 2:9, 3:6, 4:8 |
| N / V4-3 | 1 | 1 | 1 | ESC 1 / 1 | — | 2:1 |
| N / V5-3 | 12 | 11 | 13 | ESC 13 / 14 | ESC 2 | 1:1, 2:7, 3:2, 4:1, 5:2 |

The classification columns show unique-action counts followed by occurrence
counts. `ESC` is `ESCAPABLE_CHECK`, `FCC` is
`FORCED_CHECK_CONTINUATION`, and `FM2` is `FORCED_MATE_IN_TWO`.

ARM-N is the decision arm. V4-3 has one selected checking root and one
escapable checking action; V5-3 has 13 unique checking actions across 11
deduplicated roots, all escapable, with 14 trajectory occurrences and two
checking moves selected by the frozen tapes. Neither ARM-N sample has
`MATE_IN_ONE` or `FORCED_MATE_IN_TWO`.

Therefore the registered ARM-N routes are:

```text
V4-3: CHECK_PRESSURE_IS_NONFORCING
V5-3: CHECK_PRESSURE_IS_NONFORCING
overall: CHECK_PRESSURE_IS_NONFORCING
```

This is evidence that the observed ARM-N checking moves are readily
defensible in the fixed local probe. It does not prove that no deeper forcing
line exists beyond three plies. Per the pre-registered decision rule, the
search direction stops here; any next generator intervention should target
attack/check confinement geometry rather than adding search compute. No
generic agent ladder is authorized.

## Scope and verification

```text
replayed frozen trajectories: 12
new real games: 0
specialized forcing depth: 3 plies maximum
probe successor count: 1268 / 8192
generic search / AlphaBeta / BFS / training / teacher / F85 / Heavy: 0
default generator changed: false
```

Exact verification:

```text
.venv\Scripts\python.exe -m pytest tests/test_f86q_check_forcing_depth3_probe.py
6 passed
```

The durable RESULT is
`artifacts/f86q_check_forcing_depth3_probe/summary.json`. It stores compact
digests and forcing metrics, not raw action dumps.
