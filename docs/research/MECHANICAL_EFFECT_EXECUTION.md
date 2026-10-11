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


## Dedicated kind coverage addendum

After the original52-member archive was frozen/published, a separate declared
shared-template contract uses existing transform/nochange/balanced public DSL
fixtures, their normally compiled shift encodings, and4 existing bool fixtures.
58 original transition pairs and168 callback-fault cells agree, including6 shift,
16 set_current_type and4 set_bool effect occurrences. The compiler accepts these
inputs normally; no capability flag or hand-built private state is substituted.
This extends finite execution coverage of the shared variant's three previously
uncovered kinds, retaining the earlier scope descriptions and original archive.
It does not retrospectively validate the first per-pattern variant, all possible
effect interactions or live module-hook compatibility. No new timing batch or
product default follows. Evidence:data/compiled_effect_extra_20261011.json.


## Shared-template actual caller cost — distinct frozen batch

The new declaration uses all eight original roots,64 fixed512node calls and
4 completed quietD2 calls with opposite arm order. It ran05:25:07–05:25:47UTC
inside a freshly confirmed auxiliary source-only window,40.07seconds; the ACK
is not a whole-machine atomic lock. One premature preflight was rejected before
engine execution by the unchanged start guard. All decisions/non-time work and
actual backend match. Seven fixed warm roots are adverse, ratios1.002–1.123;
en-passant0.983 becomes0.997 after charging one setup to its reused batch.
Completed quietD2 is1.008 warm and1.010 with reused setup. Every individual pair
and cold/reuse row is retained. Defer this shared variant and equal-time
expansion. Lower owned code and preparation do not establish useful caller gains.

Independent auxiliaryTask026 verifies actual common generated function identity
while different original operands keep four distinct public action outcomes and
56 callback cells. Task024 separately measures1169/1139 physical Core transitions
for Core-only/Native-requested supported Shogi callers, including120 trials
outside its selected Runtime frontier wrapper. Thirty Core frontiers plusC1
is not a full physical-cost ledger. These are finite non-time observations.
The unchanged working-state seam still copies board/hands/aux and freezes/sorts
a new immutable Position. Select a new physical trial-publication attribution
question by actual consumers, including out-of-wrapper trials; first establish
transparent work/state, then judge leverage. No mutable-kernel or dominant-cost
claim follows from source inspection. Evidence:data/shared_template_cost_20261011.json.


## Concrete outside-frontier consumer attribution

A new stack-only measurement on four current-primary supported Shogi maxply2
D2 plain/instrumented callers retains exact non-time decision/stat/request
traces and actual root multiset restoration. Both arms expose120 outside-
frontier physical trials: one `initial_state` terminal-existence scan and119
`terminal_from_search_runtime` existence scans during formal push. These are
actual successful `_transition` calls, distinct from119 formal transitions.
The whole-state copy/freeze question therefore includes terminal existence
consumers as well as legal frontier production. The finite changed measurement
is not a timing comparison or evidence that freeze dominates; preserve both
zero-cell source-path harness failures. Dependency setup is pinned to auxiliary
28657a24; current primary modules are explicitly imported from cwd.
Evidence:data/physical_outside_consumer_20261011.json.
