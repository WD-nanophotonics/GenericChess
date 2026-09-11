# GenericChess F86R escapable-check defense-mode diagnosis

Status: complete. F86R diagnoses only the checking root/action pairs frozen by
F86Q. It adds no trajectory states, games, rulesets, tapes, or search. The
purpose is to identify the exact defensive reply mechanisms that break an
F86Q `ESCAPABLE_CHECK`.

## PREP authority

The final corrected PREP checkpoint is
`8f91ec82eb6741e62e27967e7d08ed0ff88ecc24`. Its manifest is
`artifacts/f86r_escapable_check_defense_mode/manifest.json`, Git blob
`51499e9a9cb19db81bcf756c48d9f5d9b538e915`. The runner blob is
`465703a062e28fdb50e320761eee39bdcae469a5`; RESULT preserves this exact
runner blob. The PREP-only correction handled empty descriptive controls
without changing the frozen manifest or scientific cohort.

PREP binds F86Q PREP blob
`76e15ba9320ab490d5d6321852eb5b683b6002fb`, F86Q RESULT blob
`84fba9e85b918895f451ce478fdabe77d8fb00c4`, and F86O manifest blob
`1d16cf69a7ce5f7347352162dcbd351485ee8c5af`. It also freezes all six
ruleset fingerprints, four PolicyTapes, all 12 F86O replay digests, and all
63 unique F86Q root/checking-action pairs from 45 selected roots. ARM-N
V4-3 and V5-3 are mandatory cohorts; ARM-F V5-3 is the positive forcing
control. L and the remaining F sample are descriptive controls.

## Exact reply and checker semantics

F86R replays the frozen F86O games and reproduces every selected F86Q root and
checking-action digest. For each checking child, a checker is an attacking
piece whose own compiled Leap or Ray geometry reaches the defender Anchor
square under the checking child's actual occupancy and ray blocking. Checker
multiplicity is piece-level; multiple matching atoms on one piece do not
duplicate the checker.

For every legal defender reply, F86R enumerates the original attacker's next
legal actions. A `BREAKING_REPLY` is a reply for which the attacker has neither
mate-in-one nor any checking continuation. The primary mechanism precedence is:

1. `ANCHOR_FLIGHT` if the defender Anchor moved.
2. `CHECKER_CAPTURE` if the Anchor did not move and the reply captured a
   pre-reply checker.
3. `INTERPOSITION_OR_SCREEN` if neither occurred and the check was removed.
4. `OTHER_CHECK_ESCAPE` otherwise.

The output retains the required independent booleans, checker squares/types,
Anchor-neighborhood coverage, legal Anchor-flight count, reply destination,
defender piece type, and exclusive primary mechanism. Contract assertions
require a nonempty exact checker set, a broken reply to leave the defender out
of check, and every checker capture to remove a pre-reply checker.

## RESULT and budget

The RESULT replay matched all 12 F86O action sequences and final digests. It
generated zero games and 1,268 specialized reply/continuation successors
against the hard cap of 2,048; truncation was false. Specialized depth was at
most three plies. Generic search, AlphaBeta, BFS, training, teacher, F85, and
Heavy were all zero. The RESULT summary SHA-256 is
`CB0D9279BFB9921EA59A18B3CB5D43BBBE253D5D8DCF528C10AFF18FA0B705F2`.

| Arm/sample | Checking actions | Breaking replies | Mechanisms | Checker multiplicity | Anchor-neighborhood coverage |
| --- | ---: | ---: | --- | --- | --- |
| L / V4-3 | 0 | 0 | — | — | — |
| L / V5-3 | 4 | 8 | Anchor flight 8 | 1×4 | 1:4 |
| F / V4-3 | 7 | 19 | Anchor flight 19 | 1×7 | 0:5, 1:2 |
| F / V5-3 | 38 | 55 | Anchor flight 49; checker capture 6 | 1×38 | 0:7, 1:14, 2:11, 3:5, 4:1 |
| N / V4-3 | 1 | 2 | Anchor flight 2 | 1×1 | 2:1 |
| N / V5-3 | 13 | 27 | Anchor flight 24; checker capture 3 | 1×13 | 0:8, 1:5 |

The `count:actions` notation in the final column is the distribution of
attacked Anchor-neighborhood counts over checking actions. Legal-reply and
breaking-reply mean/min/max values are retained in `summary.json`; for ARM-N
they are V4-3 `2.0/2/2` and `2.0/2/2`, and V5-3 `2.6923076923/1/5` and
`2.0769230769/1/4` respectively.

The ARM-F/V5-3 forcing positive control contains 15
`FORCED_CHECK_CONTINUATION` and 1 `FORCED_MATE_IN_TWO` unique F86Q actions;
all have zero breaking replies. Its 22 escapable actions account for the 55
breaking replies shown above, demonstrating that the mechanism classifier is
not labeling every check as escapable.

## Routing conclusion

ARM-N V4-3 has two breaking replies, both `ANCHOR_FLIGHT`. ARM-N V5-3 has 27
breaking replies: 24 Anchor flights and 3 checker captures. In both samples,
`ANCHOR_FLIGHT` is the strict unique maximum; no ARM-N breaking reply was
interposition/screen or other escape.

```text
V4-3: ANCHOR_FLIGHT_IS_PRIMARY_BREAKING_REPLY_MODE
V5-3: ANCHOR_FLIGHT_IS_PRIMARY_BREAKING_REPLY_MODE
overall: ANCHOR_FLIGHT_IS_PRIMARY_BREAKING_REPLY_MODE
```

The immediate generator diagnosis is therefore Anchor-flight confinement /
Anchor-escape coverage, not more movement transport or search depth. No scalar
attack-quality score, agent ladder, deeper forcing search, C2, or F85 work is
authorized by this result.

## Verification

```text
.venv\Scripts\python.exe -m pytest tests/test_f86r_escapable_check_defense_mode.py
6 passed
```

Resources: new games `0`; replayed trajectories `12`; specialized depth `3`;
generic search `0`; AlphaBeta `0`; BFS `0`; training/teacher/F85/Heavy `0`;
default generator changed `false`. The durable RESULT is
`artifacts/f86r_escapable_check_defense_mode/summary.json`.
