# Source-bound complete-history and partial action truth consumer

Current status: PRIMARY's new frozen candidate input is still
`AWAITING_FROZEN_INPUT`. Old exposed H6 records below are consumer controls,
not a substitute candidate panel or new held-out evidence. This AUX work does
not generate rules, tune search, run a Player or solve new truth.

The latest direct user correction authorizes this existing support work without
another approval question and requires an actual60+effective-minute work segment.
The earlier prelaunch approval stop is superseded; cumulative prior112.346442
minutes remain recorded separately from the new work. No old frozen run is extended.

## Actual implementation and evidence

Shared runtime is reused from sandbox
`578cd42b0672181dafa4f0bdb8015be109bd4cdc`. Only existing AUX learner differences
remain independent. Infrastructure availability is not measured acceleration.

`scripts/leaper_truth_compatibility.py` binds full semantic RuleSet, canonical
GameRecord, complete GameState/history/repetition counts, clock, setup, current
turn and Session outcome. Exact conservative identity is the default engineering
contract, not a theorem that every raw serialization byte must always match.
Metadata prose is excluded from semantic identity; proven scoped transformations
would need their own checked preconditions and are not automatically accepted.
A geometry signature, board match, root WDL match or one legal PV cannot replace
that contract. Session resignation/declaration and Core terminal are distinct.

Separate outputs describe compatibility, what was actually checked, and action
coverage. A hash/source match attributes labels but does not verify minimax truth.
The corpus reader literally replays3616published fresh roots under11available
full RuleSets and checks10936/10936legal source action labels. Family0 remains
`UNKNOWN_MISSING_RULE/MU_UNAVAILABLE`. No missing family or initially refused
setup is replaced. Source H6/repeat2 cannot label H128/repeat4.

The saved-tree consumer checks an existing full-state certificate against Core:
every supplied state, exact legal frontier, child transition, rule terminal and
local max/min label equation must agree. Missing nodes/defenses are rejected,
not solved. On the existing history packet it checks20trees,168nodes,148edges,
134terminals and10same-Position/clock history pairs. The history pairs remain
incompatible for direct label reuse. This is proof checking on supplied finite
objects, not a new minimax search or a new scientific witness.

## Partial truth and sharp bounds

Values are -1/0/1 relative to an explicit fixed seat. Convert to the current
actor before comparing choices. Unlabelled actions retain[-1,1]. Root bounds
and action bounds are different claims. Inconsistent claims are rejected.
An action with a WIN lower bound attains the WDL ceiling despite unknown
alternatives; a nonloss[0,1] bound does not establish exactDRAW or optimality.
A qualified exactDRAW root plus a nonloss action does establish WDL optimality.
At an exactLOSS root every legal choice is WDL-optimal, even though all lose.
A sole legal action is optimal without determining its value.

For actor-relative intervals[L_i,U_i] and root bounds[A,B], feasibility requires
max(L_i)<=B and max(U_i)>=A. Clip each upper bound atB. Raise actioni's lower
bound toA only if every other action has upper bound belowA. These projections
are sharp: every retained endpoint has a feasible completion.
The exact one-decision regret interval fori is
[max(0,A-U_i,max_other(L_j)-U_i), max(0,max_other(U_j)-L_i)].
A sole action has regret0. Zero upper regret proves optimality; positive lower
regret proves suboptimality; otherwise the classification remainsUNKNOWN.
These statements concern attributed WDL bounds, not mate speed, heuristic score
or opponent-specific win probability.

For two actually selected actions in the same context, the consumer reports
sharp candidate-minus-baseline value bounds. The same action cancels to[0,0]
even if its value is unknown. A different unlabelled action remains uncertain;
these are finite one-decision bounds, not an Arena result or confidence interval.
Exhaustive literal completions for1-4actions check the interval formulas and
seat reversal, with separate paired-action completion checks.

## Label-count information diagnostic

We enumerate every exact-label subset on all39value-multiset patterns present
in the3616old source frontiers, with root counts retained. This is a hypothetical
information budget: one label is not a measured unit of certificate cost.
Every pattern's exhaustive result also agrees with an independent closed form.

Forn>1, letm be the number of actions aboveLOSS andk the number attaining the
known true maximum. With the root value unknown, one optimal action needs one
WIN label if aWIN exists; otherwise it needsn-1labels whenm<=1, andnlabels when
m>=2. Classifying every action needsnlabels. With an exact root supplied,
aLOSS root needs0action labels; other roots need1label to identify an optimal
action andn-1labels to classify all only whenk=1, otherwise n. A sole action
needs0labels in all cases. Lower bounds follow by assigning adversarial values
to any omitted labels; these are identifiability statements, not label acquisition
policies or permission to inspect oracle labels when selecting training starts.

On the existing corpus, an exact root allows an optimal choice to be certified
with0action labels at696roots and1label at2920roots. Without root truth the
minimum histogram is0:488,1:928,2:960,3:744,4:376,5:112,6:8. These counts do not
choose a new PRIMARY panel and do not establish useful difficulty or search gains.
Coverage fraction alone therefore does not determine decision identifiability.

## Collaboration and limits

GitHub Pro183742at the source above is adopted for AUX role/scope. Solicited
Slack Dot reply1793009276.470739 independently read reports only; its advice to
separate compatibility/qualification/coverage and retain partial bounds was
adopted and implemented. It did not execute the new consumer or approve scope.
The new user instruction, not that reply, resolves the old repeated-approval stop.

No new Player, solver, game, build, candidate generation, H6syntax cache iteration,
1520return rerun, production default, PRIMARY state write or scheduler change.
Actual source data remain exposed controls; missing PRIMARY inputs stay explicit.

Current concrete milestone is published while the research segment remainsACTIVE;
this is not a60minute completion claim. End-to-end CLI:
`python -m scripts.qualify_leaper_candidate_truth --candidates INPUT.json --output OUTPUT.json`.
INPUT is an explicit list of{id,rule,record,selected_action(optional)}. No input
is auto-generated. The preserved historicalPRIMARY p53record lacks a complete
RuleSet in its own envelope and correctly returnsUNKNOWN; the consumer does not
guess a rule from its name or borrow H6 labels. Resignation mismatch returns
INCOMPATIBLE with no action coverage.

Source pins and compact results are in[data/aux_truth_compatibility_20261026](data/aux_truth_compatibility_20261026/).
At this milestone124relevant headless checks passed, including38newsemantic checks.

## One-sided proof qualification and explicit history revalidation

The consumer also checks a finite supplied strategy bound. For aLOWER bound
at a named seat, that seat supplies one legal move and the opponent supplies
every legal defense. UPPER reverses those quantifiers. Every reached leaf must
be an actual Core terminal satisfying the bound; a heuristic/caller cutoff is
not a terminal. Missing nodes, illegal moves and incomplete universal frontiers
fail. Declaration/claim choices are outside this move-certificate format and
are explicitly rejected because ordinary legal_successors does not enumerate
them. This fixes a scope guard in the first consumer milestone; old H6 results
are unaffected because those worlds have no declarations.

The160old supplied one-sided checks cover both fixed seats and every valid
source threshold;80are informative and80are the trivial WDL range boundaries.
They are not160independent positions. Selected moves use public apply_action;
universal nodes use complete public legal_successors. Node/edge counters describe
checked objects, not whole-call speedups or an engine optimization.

Three actual old-proof controls compose the interface: (1) a one-node child
checkmate proof certifies one WIN action while5other legal actions remain
unlabelled; (2) a certified nonloss action staysUNKNOWN without root truth and
becomes optimal when an independently checked exactDRAW root is supplied;
(3) a3node cooperative draw path from aLOSS root fails because it omits a legal
opponent defense. These are exposed validation controls, not new test roots.

An explicit revalidation function can replay a supplied strategy skeleton on
another existing incoming history with the SAME full rule, Position and clock.
It never changes the default exact-context mismatch. It follows only supplied
existential moves, checks all universal defenses and produces a fresh target
full-state certificate. If a source terminal leaf becomes ongoing, no missing
continuation is searched. Earlier actual target terminals are accepted only
when they satisfy the requested bound. Failure means this certificate did not
prove the target bound; it is not disproof or opposite WDL.

Across the fixed10old history pairs, two directions, two seats and source-valid
thresholds,68/160checks revalidate and92do not. Among the80informative bounds,
26revalidate and54do not. All accepted bounds agree with the already checked
target full-tree labels;64of the92unproved cases nevertheless have a true target
bound. These counts measure supplied-certificate portability, not strength,
independence, win probability or a new quality panel.

A particularly small actual control has a3node source exactLOSS certificate
whose sole terminal is checkmate. It contains no repetition terminal. Another
incoming history reaches a repetitionDRAW before that mate, so the exactLOSS
upper bound-1fails. Replaying the SAME skeleton with the weaker nonWIN upper
bound0succeeds. This distinguishes exact three-valuedLOSS from binary disproof.

[Kishimoto and Müller, AAAI2004](https://cdn.aaai.org/AAAI/2004/AAAI04-102.pdf)
uses checked tree simulation when a proof is reused under another path. Its
proof semantics and draw/UNKNOWN distinction matter when adapting that idea;
the paper discusses separate threshold searches for draws. Its reported search
costs are not measurements of this consumer. The present result is a scoped
application with actual full-history Core checks, not a general GHI algorithm
or production transposition-table deployment.

## Sufficient history conditions for these fixed proof skeletons

The following derivation applies only to the frozen plain H6/repeat2 worlds:
physical transitions and static terminals are Position-local; incoming history
can add a repetitionDRAW; clock and static-terminal precedence are unchanged.
It does not cover generic history-triggered effects, declarations or heuristics.

Letc(p) be the source root's prior count of Positionp, including the root if
applicable. At a supplied proof nodex, letv_x(p) be its count minusc(p), the
number of future visits along that source path. Letc'(p) be the target root's
counts andq=2. The guard study checks each source certificate first and uses
only already supplied proof nodes; it never discovers a future game graph.

For aLOWER boundb<=0orUPPER boundb>=0, a new earlier repetitionDRAW satisfies
the bound. The only potential fall-through is a source repetition leaf which
would become ongoing on the target. A sufficient condition is
c'(p)+v_x(p)>=q at every such leafx. Leaves for the samep combine by taking
the largest required prior count. Static or clock leaves need no such count
guard: they remain terminal unless an earlier harmlessDRAW intervenes.

For the strongerLOWER1orUPPER-1, every new earlierDRAW would violate the bound.
A sufficient condition is c'(p)+v_x(p)<q at every supplied ongoing nodex.
Combine repeatedpconstraints by the smallest allowed prior count. The source's
winning static terminal leaves remain winning under the same Position/clock.

Soundness follows by induction on the finite supplied tree. At existential
nodes the same verified move remains a witness; at universal nodes all physical
defenses remain covered until a permitted earlier terminal. The conditions above
ensure every path either reaches a source terminal with the same outcome or
stops earlier at an allowedDRAW. No target leaf is filled with an assumed label.
These are sufficient conditions for a particular bound and proof, not whole-game
history equivalence and not permission to share finite-depth heuristic values.

On all160fixed checks,66guard passes all revalidate. Two further strategies
revalidate although their sufficient guard fails, because an earlier target
repetition shields a later source leaf. Thus the guard is deliberately incomplete.
Requirements mention0-3Position keys in this corpus; that is not a measured
runtime saving or a proposed replacement TT key. Failed guards require explicit
proof replay orUNKNOWN, not a false WDL conclusion.

## Fixed-denominator comparison bounds

For ONE matched complete context, repeated queries share the same unknown action
values. We coalesce exact rational candidate-minus-baseline coefficients before
bounding a weighted sum. A->B andB->A with equal weights cancel exactly even if
both action values are unknown. Missing/failed slots keep their planned weight
and a worst-completion difference range[-2,2]; no game result is assigned to a
failed call. These are deterministic partial-information bounds, not confidence
intervals or an assumption that repeated observations are independent.

For linear coefficientsd_i and actor-relative action intervals, independently
minimize eachd_i*v_i subject to the root upper bound. If that minimizing vector
fails to attain the root lower boundA, force one eligible action toA using the
smallest objective penalty. Negating coefficients gives the upper bound. The
result is sharp over the stated interval relaxation; actual game semantics may
impose further correlations. Exhaustive literal completions independently
check the formula, rational weights, shared-variable cancellation and missing
slot denominators.

## Completing the historical PRIMARY source envelope

The original p53branch envelope alone lacked its full RuleSet. Its published
README points to the exact historical input packet at sandbox
`578cd42b0672181dafa4f0bdb8015be109bd4cdc`,
`docs/research/data/leaper_ordering_diagnosis_20261025/next-default-panel-inputs.json.gz`.
Following that link recovers the actual rule rather than guessing it. The
branch envelope's decoded-source SHA, full record and named rule key match.
Literal replay qualifies64complete contexts and603/603source action labels,
including the exact prepared p53root. They are one full rule/two old TRAIN
trajectories, with34all-action-equal contexts, not64independent rule samples.
The actual rule clock is64/repeat4; no H6 truth is transferred.

An initial reader check failed because it treated the published rule-key SHA
as compact JSON. The source key instead hashes sorted JSON with default spaces;
it is also distinct from the semantic RuleSet fingerprint. The corrected reader
checks all three meanings separately. Missing/unknown labels remainUNKNOWN,
and source WDL remains attributed rather than independently re-solved.
The frozen packet'sPREPARED_ONLY marker is retained as input metadata and does
not overwrite separate historical execution records. No new query was launched.
New PRIMARY cross-rule candidate status remainsAWAITING_FROZEN_INPUT.

### Source method review for the recovered64/repeat4 labels

The packet points to fixed public source
`26d414cce26d44e7d2cfae84a20195fa715f2906`.
Reading its`scripts/leaper_four_actor_history.py` and the existing
`leaper_history_barrier_rank.py` identifies the actual qualification premises:
a complete qualified alternating Position graph; injective repetition identities;
position-local plain Leaper legality; remove-from-game captures; no promotion,
drops, claims or additional history adjudication; automatic repetitionDRAW and
clock64; static terminal precedence. The producer checks this exact full rule
fingerprint and source graph/qualification hashes. This reader did not execute
that solver or independently replay the complete graph/rank certificates.

The reduction treats prior countq-1 nonterminal vertices as DRAW barriers,
excluding the currently playable root. A strict winning attractor rank decreases
along every required defense, so its winning strategy does not revisit a future
vertex. A vertex with lower incoming count cannot reach the repeat threshold on
that acyclic continuation. Thus lower-count future repetitions do not invalidate
a certified strict win within its remaining rank/clock. For residualDRAW states,
additional draw stops preserve nonloss strategies. Rank beyond the remaining
clock becomesDRAW rather than an available unbounded-horizonWIN. These
arguments need the stated complete-domain and terminal premises; they do not
license a partial graph or generic history-sensitive rule reduction.

Ignoring an incoming key outside the source graph is justified only by a complete
forward-closed domain which cannot reach that Position again. Checking the root's
current count alone would be insufficient. The recovered panel's literal replay
compares the full incoming count map, not only that one count. Source method
review and literal source binding are now explicit; actual complete graph/rank
reverification remains outside this segment and is not claimed. Existing capped
or partial checks are not refilled.

## First safe segment checkpoint

The segment confirms3692.080816seconds=61.53468effective research minutes.
Recovery, Slack transport, publication and closing configuration are excluded.
146headless regressions pass after the final perspective-binding correction:
locally certified action labels carry their named value_seat, and a consumer
requesting another seat rejects the mismatch. No whole-field truth re-solve,
Player call, game, build, extra worker or default activation occurred.
Prior related112.346442minutes remain carried; this round's actual entire
elapsed/closing cost is additional, not reset by the new session. The user's
latest explicit standing authorization resolves the previous repeated-approval
stop. Session/accounting records are source receipts, not a universal audit of
agent cognition. This work reaches a safe scientific checkpoint; the project
and future frozen-input compatibility task remain open.

## Closing Pro update and newly available PRIMARY sources

Before publication, remote sandbox advanced to68f83ff02067b7d557b12eb1438e066504bfa192.
Its new20:07GitHub Pro review was saved/read in full. No production generic_chess
changes occurred after this segment's fixed shared-runtime source. Adopted and
executed the new AUX instruction: qualify ALL24published v2contexts/12rules,
without generating candidates, extending H6truth or taking PRIMARY profiling.
The earlierAWAITING_FROZEN_INPUTobservation remains true at its original time;
current source availability isAVAILABLE_SOURCE_NOT_ASSIGNED.

The [new table](AUX_PRIMARY_SOURCE_COMPATIBILITY_20261026.md) records full rule
fingerprints, actual preludes/history/clock/repetition/Session state, H6mismatch,
254UNLABELLEDactions and explicit behavioral coverage.24existing saved game
records/1979plies were literally replayed; no new games or policy calls occurred.
Their actual outcomes are not root/action minimax labels.12of24contexts have
saved game coverage; the other12remain without behavioral records.

Final scientific checkpoint after the closing Pro task: 4191.248084confirmed
seconds = 69.85413effective minutes,147checksPASS. The initial61.53minute
checkpoint was extended in the SAME session to execute the newly published Pro
instruction; no timer, identity, costs or confirmed work were reset.
