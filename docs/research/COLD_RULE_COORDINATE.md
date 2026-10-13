# Cold rule input and exact coordinate allocation

Current production change: `square_to_index` uses direct row-major arithmetic
only for an exact builtin positive `int` extent. BoardShape, int subclasses,
bools and invalid extents retain the original validation path. No state cache,
evaluator weights, search defaults, Native ABI or UI policy changes.

## Input clocks and actual caller

36 actual default-player calls cover Chess/Shogi and four new generated8/12-board
rules, two repetitions each of cold private disk, new disk-hit cache and shared
memory-hit cache. All six retained action/score/full-PV/depth/provenance tuples
per rule agree; time-limited attempted work need not agree. Full history and
Core PV legality hold. Actual Native legality is present in every cell.

Imports are outside the clock. Rule generation+compilation, session/prefix8,
player constructor and choose_action search are separate stages. Cold constructor
cost0.014–0.116s versus about1s search; profile builds0.0097–0.0668s. Existing
profile caches already remove that rebuild. New shared-cache/framework work is
not selected. The six compile/generation clocks span0.040–0.386s; these include
built-in definition construction or generated sampling and are not one isolated
compiler primitive. Cold-to-warm order and ordinary concurrent load limit timing.

Larger allowed inputs change that local scope: prospective8/12/16/20-board rules
add8 actual first decisions. The20 constructor costs0.69–0.70s, compile0.382s,
so setup can matter to a1s caller. No old declaration is extended. Mechanics,
type counts and size jointly change; no isolated size causal ratio follows.
Actual16 Native compilation works, while20 is rejected by the existing<=16/
256-square Native range and uses complete Core. Incoming full-prefix metadata
is present at12/16 and absent for this20 rule; unsupported acceleration is not
an unsupported game. Defaults and Native limits remain intact.

## Actual work attribution and minimal change

Four cProfile D4 calls on fresh12-board1843/1844 compare requested Core/Native
under the same public default geometric evaluator. Within a root completed
D4/nodes/score agree. Profile overhead changes timing; these are attribution,
not speed controls. Core shows30–44M cooperative helper/context polls. Native
exposes1.37M/1.30M square_to_index calls with1.49/1.54s cumulative profile cost.
The existing SemanticAttackEvaluator changes attack authority (e.g. pawn capture
versus movement geometry); it is not a drop-in speed control for this evaluator.

20580 finite positive-int/rectangle/subclass/invalid-extent and malformed-square
comparisons retain values AND errors, including old out-of-bounds arithmetic.
16 counterbalanced actual fixed-depth cells on1841–1844 retain all non-time
PlayerDecision fields, work counters, PV and history. Local whole-call savings:

| Rule | Board/depth | Order0 | Order1 |
| --- | --- | ---: | ---: |
| 1841 | 8 / D3 | 10.41% | 7.06% |
| 1842 | 8 / D3 | 4.42% | 6.62% |
| 1843 | 12 / D4 | 3.74% | 6.10% |
| 1844 | 12 / D4 | 4.71% | 4.03% |

64 actual fresh1851–1854 Core/Native q0D2/q4D1 calls preserve every non-time
output/work field in16 four-cell groups. All roots stay; no resampling or human
labels. Declared2000-node/8s/hardq8 conditions and actual providers are retained.
These small development rules are not the entire generated domain.

24 actual4/16/64s cells on Shogi and1844 retain all12 complete result tuples and
depths. More attempted work does not establish a deeper/useful decision or Elo.
The source change qualifies a cheap allocation reduction, not a strength claim.
Final2356 active tests and105 focused tests pass, zero errors/failures/skips;
seven new public-invalid-extent cases cover bool/type fallback. A nonfatal
existing default pytest-cache write warning is retained, not a scientific block.

## Alternatives and delivery

A private narrow Core board-candidate callback alias preserves six fullfrontiers
and132 paired injected interruption points (264 failure invocations). Eight D4
search calls preserve full non-time/work output; savings0.49/-0.16/0.49/0.98%
are small/mixed, so leave the original method. Total profile poll time cannot
be attributed to just its five sites. No polling frequency is reduced.

Complete evidence and source hashes are bound by
[data index](data/cold_rule_coordinate_20261013.json). Science-only archive excludes
raw Slack/account records, host XML, user/private input and credentials. Partial
and failed producer sources/corrections are retained. Consumer process restart
loads the coordinate change; no new option, Native build or UI integration task.
The separate prefix-free incoming schedule is a private feasibility result,
not production code: [report](PREFIX_FREE_INCOMING.md).
