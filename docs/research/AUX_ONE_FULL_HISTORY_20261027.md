# One full H128 history: typed actions, terminal fact and proper-prefix control

The preselected first pilot slot is128plies. Its unchanged semantic GameRecord
replays through the existing semantic adapter to current Core MAX_PLY/DRAW.
Deleting the final action produces127plies/ONGOING; the maintained learner's
terminal reader returns None, not0. No new play, Player, training, solver, rule,
archived producer execution or other-slot outcome analysis occurred.

The raw-record/default-legacy attempt FAILED and remains a negative result:
RuleSet shape alone selects CompiledRuleSet, while all128 archived actions are
SemanticBoardMove. Current Core rejects the first typed action
legacy_014:g15:a1-b2. This does not show the old game was illegal or the current
random-opening learner was broken; its CLI does not import these records.

## Fixed selection and preserved recovery

Plan froze one original record, at most4replay attempts,20minute whole check,
before outcome inspection. Source packet at sandbox864bc2174ba1e6011ce85e1c68fbdd4b7d455705:
docs/research/data/leaper_forward_design_20261022/observations.json.gz,
blob98a6e8cafc8207c016facc6dc5f5e6808142d7da,
SHA25665cbda6e861249f04914511f5bcdd1e83233879c276236df7caac1f7d5c0b761.
Selection: runs.pilot.results.slots[0], bound to games[0], runpilot/slot0/world0.
No winning-family, policy or terminal filter. Original slot says failed, later
recovered finished; that old aggregation/recovery status is retained and is not
equated with this study's compiler/action-type failure.

[Input](data/aux_one_full_history_20261027/input.json) binds exact full rule and
records, SHA25662541ed42c093b8ce420131f364ef40c863a80cd8b3058e6da5e85e66b24a2aa.
Original receipt SHA is a source claim; this study verifies the packet/input
bytes, not an absent historical executable tree or original receipt byte file.
No H6/repeat2 label, old cache cap or PRIMARY computation grant was reused.
Current rules/history/runtime baseline is own0ebfa9dd with committed d896c606
infrastructure unchanged; no new mainline implementation was duplicated.

After the first failure, the original claim stopped NO_GO. An explicit diagnostic
amendment preserves that result and the SAME input/deadline/four-attempt cap.
Three remaining calls test the correct shared semantic route and one marked
coordinate projection. No alternate slot or extra replay allowance was added.
A preliminary geometry-only verifier assertion accidentally included disabled
drop templates; source/failed receipt are retained. It failed before any further
replay. Skipping only proved-disabled drops repaired that verifier, not the game.

## Actual four-attempt ledger

|Attempt|Record/product|Result|Learner terminal value|
|---|---|---|---|
|1|Original semantic record/default legacy product|Rejected first action|Not produced|
|2|Original semantic record/shared semantic product|128plies,MAX_PLY,no winner|0|
|3|Original proper prefix/shared semantic product|127plies,ONGOING|None|
|4|Explicit projected BoardMove record/legacy product|128plies,MAX_PLY,no winner|0|

[First failure](data/aux_one_full_history_20261027/result.json) is not overwritten
by the [diagnostic result](data/aux_one_full_history_20261027/diagnostic.json).
Three successful saved-record replays commit383archival plies; they are not new
games or new policy decisions. The128step full record has129history entries,
87repetition keys,maximum count3,current count3. Prefix has128history entries,
87keys,maximum3,current count2. The terminal is the128ply clock, not a fourfold
repetition or an arbitrary caller draw.

The finite projection retains coordinates/promotion only and deliberately
changes action identity: original and projected GameRecords are unequal.
Existing hash-footprint admission plus192 type/mode/owner/source checks exclude
coordinate aliases for THIS original plain-Leap rule. No general semantic-to-
legacy adapter was added. Overlapping patterns, custom effects, drops/promotions
or other semantic DSL rules cannot inherit this projection.

Full projected-legacy and original-semantic executions have equal final physical
state/result and ALL129exact Position witnesses. Raw repetition maps differ,
but an injective observed87key relabeling matches their counts. Actor/check flags
also align. This is the observed trace, not a general TT quotient, hash mapping,
future-tree bisimulation or speed claim. The verifier reads Core-owned immutable
GameSession._search_witnesses; this is not a new public learning/runtime API.
Different key payloads are expected: semantic_position_key includes canonical
aux_state even when empty, whereas legacy keys retain their historical encoding.

## What this licenses

One CURRENT fixed-rule legal trajectory ends in an actual draw; its proper
prefix remains an ongoing game. The terminal fact does not label the initial
state, counterfactual actions, every continuation or another clock/repetition
rule. It does not reproduce the old controller, prove learning gain, or permit
oracle-selected experiential starts. Existing full GameSession replay is enough
to rebuild this history; fingerprint/Position equality is insufficient to copy
keys or erase typed action identity.

Both full-record terminal readings are actual current consumer calls; no accepted
TD observation, weight update or hypothetical action value was measured. Keep
None for the actual127ply session result even when later mathematical bounds
might constrain that state's strategic value. No learning/strength experiment
or extra record sweep follows this single case.

Drivers: scripts/replay_leaper_first_history.py and
scripts/diagnose_leaper_first_history.py; exact executed copies, initial static
diagnostic failure and immutable plans accompany the data. Timing is small
in-driver work, not complete invocation/research cost or a backend benchmark.

## Final-edge strategic interpretation (no further execution)

A separate interpretation of the already closed four-attempt evidence uses no
additional replay, action enumeration, search or sample. Core constructs initial
side0 (semantic_executor.py:635), and each board transition flips side
(:1799); the127ply prefix is therefore owner1-to-move.
The verified128th action is K from(3,2) to(3,1), semantic pattern legacy_008/g12.
For owner0 payoff {-1,0,+1}, this available terminal-draw edge gives V0(h127)<=0
(and V1(h127)>=0) under ordinary adversarial play. Owner1 can choose that edge
and guarantee a draw; another legal action might instead win. The verified
edge therefore certifies a non-losing option, not optimality or exact DRAW.

The max-ply clock alone cannot strengthen this to equality. Both semantic
executor terminal_result (semantic_executor.py:1890-1968) and legacy
_terminal_from_parts (terminal.py:244-312) test absence of legal actions and
checkmate/stalemate before max-ply. A different final action could change that
earlier adjudication; none was examined. We do not assert that such an action
exists in this particular prefix. Exact equality would need the missing lower
bound for owner0, which the recorded draw edge does not supply.

The bound is history-and-clock-specific. It cannot be propagated to the initial
root along the single observed path: an ancestor's other actions and opponent
choices remain unexamined. Physical Position equality alone cannot transplant
it to another history, clock or repetition rule. FixedScaleSessionEnv's actual
terminal reader (incremental.py:402-406) still returns None at the ongoing
prefix; a mathematical bound is neither a terminal observation nor an accepted
TD target. No oracle-selected training start or learner modification follows.

Cost qualification: scientific replay/diagnosis stopped03:02:00UTC before the
original02:42:38+20minute boundary. Git publication completed03:03:07UTC, about
29seconds beyond that whole-task deadline. The nominal20minute whole-check
promise was therefore not met for delivery; this overrun is retained, with
publication administrative and excluded from effective research credit. The
interpretation above does not reset or extend the closed four-attempt budget.

Explicit inference: V0(h127)=min over legal choices of owner0 terminal payoff;
the known choice has payoff0, so V0 is in[-1,0], while V1 is in[0,1]. The
observation supplies no inequality forcing V0>=0. This is a bound on strategic
value, not an interval estimate with sampling confidence. No independence,
population generalization or empirical strength follows from this single trace.
