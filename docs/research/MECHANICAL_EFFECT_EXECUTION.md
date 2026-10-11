# Mechanical effect execution, finite control —2026-10-11

Question: can mechanically specializing declared effect kinds and expanding
ordered effect loops reduce actual caller cost enough to justify compiler
ownership? This is a private prototype, with ordinary product execution,
backend, q/evaluation and the frozen UI unchanged.

Waugh's [generated GDL state queries](https://www.cs.cmu.edu/~waugh/publications/giga09.pdf)
and the [Regular Games automata model](https://ojs.aaai.org/index.php/AAAI/article/view/40203/44164)
provide primary examples of mechanical rule compilation and explicit runtime
interfaces. Their games, rules, Monte Carlo comparisons and compilation costs
are different. No numerical speed factor or semantic proof transfers here.
The local prototype copies the original transition AST and specializes only
literal effect-kind dispatch and declared effect order. Dynamic square/type
operands, guards, ordered auxiliary lifecycle, triggers, promotions, checkpoints,
terminal/history and original material remain authoritative.

One exact prepared semantic object and exact original pattern object select the
private function; other carriers fall back. Pattern/effect records are frozen;
unsafe mutation is outside this preparation assumption. Initial continue
expansion failed before execution and is preserved with its correction. Module
function substitution is not transparent: an original `_apply_effect` fault
hook raises, while copied specialized functions bypass it. This is a recorded
instrumentation compatibility limitation, not a new development approval gate.

The original unmodified transition oracle matches440 legal root transitions
across8 builtin and5 pure semantic fixtures, and628 precise callback-fault cells.
An independent mixed8ply oracle matches275 public children with full state/hash,
history and undo; its initial shared-oracle harness source remains preserved.
The18 existing tests mostly select other carriers and do not certify this new
compiled path.8 lexical minimalAB D2 traces retain work and actual backend.

Default generated legacy carriers have no IR; direct semantic-DSL compilation
rejects no semantic actions. These failures remain. The existing explicit public
legacy-to-semantic entry separately supports4 generated board4/6 seed7/21 roots:
48 transition pairs and90 callback-fault cells match the unmodified oracle.
This is explicit route support, not the full generated domain or default selector.
Executed effect kinds are move/remove/set_token/clear_right/clear_token/
remove_from_hand/place; shift/set_bool/set_current_type lack dedicated effect
execution coverage here, so no all-kind compiler acceptance is claimed.
One initial nonexistent generator parameter and one import typo failed before
engine cells; their source/errors are preserved separately from semantic results.

25 Chess and155 Shogi patterns generate108138/629889 source bytes. Shallow owned
code objects total78976/461448 bytes; function objects12000/63040, dictionaries
40432/248848, plan tuples1400/8680. These exclude borrowed IR/module objects,
constants and allocator overhead; source size is not retained heap size.
A structural alternative has6/3 effect-kind sequences for those25/155 patterns,
and3 sequences for each of4 generated inputs. Shared code retaining actual
pattern operands is a possible new premise, not an accepted implementation.

Caller cost and the resulting decision are recorded below after the single
predeclared64 fixed512node and4 completed quietD2 control. Preparation is measured
separately and included in explicit cold/amortized accounting. No equal-time
expansion or performance claim follows from semantic agreement alone.
Evidence:data/compiled_effect_20261011.json and its source/failure/result archive.


## Actual caller and preparation costs

The declared64 fixed512node and4 completed quietD2 calls ran05:10:07–05:10:51
UTC,43.77seconds, within the explicitly confirmed source-only window. ACK is
not an atomic machine lock or a whole-machine-idle guarantee. All returned
choices, scores and non-time work match; original Native route remains.
Warm fixed aggregate ratios range0.891–1.575; three roots are adverse, with
individual paired outliers retained. Completed quietD2 is about1.000x. Each
fixed reused batch becomes worse after charging its one compiler preparation;
those ratios range1.098–7.295. One-call cold and descriptive amortization are
separate records, not independent completion forecasts.

Defer this per-pattern prototype and equal-time expansion. Semantic agreement
and source specialization did not produce useful completed-caller savings here.
A separate next premise can share generated transition code by effect-kind
sequence while reading actual frozen pattern operands. It must first establish
construction/ownership benefit and finite semantic/callback agreement; it does
not merge public actions or establish a full generated state engine.


## Shared-template construction, distinct premise

The next finite implementation is actually constructed: one transition per
ordered effect-kind sequence and one helper per kind, reading actual original
`pattern.effects[index]` operands. Public action/pattern identities remain
separate. This preserves the same440+48 transition pairs,628+90 callback cells,
275 mixed public children and8 minimalD2 traces against the original executor.
It has one copied module environment,13/7 function/code objects and6/3 transition
templates for Chess/Shogi. Generated source16366/9961bytes and shallow owned code
13064/7616bytes are lower than the first variant's108138/629889 source and
78976/461448 owned code. Functions2080/1120bytes, dictionaries2416/4912 and
plan tuples1400/8680 remain. Descriptive preparation0.020/0.012s is not a
controlled speed ratio. Original board/hand/aux copies and Position construction
are still present. Copied-global/live-hook compatibility and uncovered effect
kinds remain limits. Keep it private; its warm/cold caller behavior is unmeasured.
A new controlled caller question can test whether lower preparation survives
extra dynamic operand lookup. No first-variant timing is relabeled as this result.

Independent auxiliaryTask017's16 actual maxply2 StandardShogi callers preserve
D2/121nodes but Native-requested final eligibility1 coexists with actual C1 and
30 Core fallback frontiers. All152 observed requests are ongoing,121 cache-served;
the initial primary uppercase-status aggregation error is preserved and corrected.
Task018's exact final Runtime hash independently retains8 comparison/retry cells:
two forced-collision faults reached once; six controls include armed singleton
cases with no comparison. This supports the final scoped migration repair, not
execution of the primary2083 tests or independent performance measurement.
Own adoption/source hashes are archived; new auxiliary publication was not yet
verified when these working records were read.
