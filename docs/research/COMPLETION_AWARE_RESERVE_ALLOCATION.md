# Completion-aware reserve allocation —2026-10-15

Science remains OPEN. This is a caller-policy experiment on the unchanged
PUBLIC backend at `a3c495916f81a2f1fdb50f2b0344a9f5463583f4`. It changes no
product defaults, evaluator, rule semantics, Native implementation or API.
PRIMARY owns this experiment; the separate DEV_AUX solver/bank/learning lane
was neither edited nor duplicated.

## Question and actual policy

The preceding q-control found a literal one-reply loss in the enabled-q first
reserve at4323/12. Disabling q entirely avoids that immediate reply there, but
other exposed continuations warn against a global q switch. The new question
is whether a cheap deeper disabled-q reserve can provide a better fallback
without displacing useful requested-q completion under the SAME caller deadline.

The fixed candidate assigns a.25s reserve target to disabled q, then gives actual remaining
caller time to enabled ordinaryq4/hard8. The single-call controls are disabled
q and enabledq4. All arms use the physical-root-win goal, maxD16, TT0, no ordering
cache and one million TOTAL internal budget nodes. The API exposes main `nodes` and
`qnodes` separately; only their SUM is total work. The first call has disabled q
and actual zero qnodes, so subtracting its main nodes is exact for phase2.
Inputs are precompiled
and priced; engine construction, packing, kernel execution, returned PV checking
and phase decision/record conversion are charged. Full initial admission is
outside this per-move experiment, and scientific audits/file saves are separate.
A common.02s delivery reserve is subtracted in all arms. The outer monotonic
clock is authoritative; kernel elapsed alone is never the remaining-budget basis.
Final artifact serialization after the final decision is separate recording work;
execution eligibility is checked after that conversion. No hard timer guarantee.

The second phase replaces the disabled reserve only with an actual retained
`main_iteration`, depth at least2 and retained ordinary/hard policy(4,8).
A later time/hard abort DOES NOT invalidate an earlier completed requested-policy
iteration. A completedD1/(0,8) cannot replace the deeper disabled reserve. Numeric
scores from these distinct finite objectives are never compared. A physical
checked winning root child is a separate valid evidence source atD0 with no
completed q fields. A single cancellation token persists across both calls;
cancellation/outer expiry forbids execution even if winning evidence remains.

This is a new decision goal versus the earlier finite-analysis q study, with
new timing margins/caps; old560query records and one-secondUNKNOWNs are frozen.
No retrospective relabel, silent hard-q change or claim of identical policies.

## Initial mechanism check

Three exposed roots4323/12,4312/4,4313/0;1/4s, three arms, two reversed orders:
36queries complete in101.913s. Every selected PV,132edges, matches Core/Native
board, hands, auxiliary state, actor and complete identity/event histories.
At4323/12 and1s, q4 retainsD1/(0,8) and permits a literal quiet checkmate reply;
the candidate retains its completedD3disabled reserve, whose complete reply
frontier has no immediate opponent win. At4s it instead adopts requestedq4D2.
On the other two roots the candidate retains the same q4 action, despite losing
one main depth at1s. These are mechanism observations, not optimalWDL, strength
or evidence that a deeper reserve is always preferable.

Eleven narrow control cases pass: real Native calls cover between-phase
cancellation, actual physical wins and complete state preservation; separate
synthetic retained-result and clock controls explicitly test the decision
contract. A final stop reason alone is insufficient, mate-like scores do not
replace physical evidence, and cancellation never authorizes a move.
One control-script SyntaxError was corrected before any control execution;
there was no OS/SAC blockage or user intervention requirement.

## Transfer and contrary evidence

The frozen transfer closes all20families in2074.568s:70of80planned roots,
840of960planned queries. All120missing slots are the10actual terminal tails;
no family/whole cap was extended and no input was replaced. All840queries
audit every returned phase PV,3274edges, against complete Core/Native history.
There are280matched triples (same parent/budget/order),224with the same q4 and
candidate action. Two-order repetitions are not independent roots.

|Board|Budget|Triples|Same q4/candidate action|Requested q policy displaced|
|---|---:|---:|---:|---:|
|4|1s|20|20|0|
|4|4s|20|20|0|
|8|1s|40|36|0|
|8|4s|40|38|0|
|12|1s|40|20|2|
|12|4s|40|28|0|
|16|1s|40|30|4|
|16|4s|40|32|0|

The6displaced requested-policy receipts are only3parent/budget cells:4322/8,
4333/4and4333/12at1s, each repeated twice. The latter two retain the SAME
physical action despite different policy fields. No requested-policy completion
is gained. The candidate selects170requested-q results,78disabled reserves and
32physical wins, counted as receipts rather than independent successes.

The only complete new immediate-loss contrast remains4323/12at1s, repeated in
both orders: q4permits actual mate, candidate has a complete one-ply frontier
without an opponent win. This is one exposed parent, not two independent gains
or optimalWDL. Unique diagnostics contain106complete no-win scans,8actual child
terminals,1winning-reply witness and1UNKNOWN at its original2s diagnostic cap.
No complete paired converse immediate-loss witness was observed; that is not
evidence of no long-run regressions.

All280q4/candidate pairs pass their recorded delivery gate. One q0control does
not:4315/0,4s,order0 has pre-final-serialization wall3.998279s, then expires at
the later delivery check. Therefore even a zero saved pre-serialization overrun
does not imply all complete caller returns meet the deadline. The.25s reserve
target actually reaches.264229s because Native packing/PV work is atomic; actual
phase wall is deducted before phase2. The maximum observed phase-wall minus
kernel elapsed is.018726s. We report these limits rather than a hard timer.

## Two bounded existing-API alternatives

A NEW24query contrast on three preselected exposed parents caps the reserve at
D2, or transfers its completed legal action as a root-order hint. No tree/bounds
or cross-objective score transfer. At4323/12the cappedD2reserve takes.0287/.0276s
versus original.2586/.2600s, preserves the no-immediate-loss frontier and leaves
about.951/.952s instead of.721/.720s for phase2. At4312/8it restores requested
q4D3where the original/hinted reserve retainD2. This is a finite-policy coverage
observation, not a value/strength guarantee. The hint alone gives no corresponding
recovery in these cases and is not selected for further work.

The4322/8q4control itself straddles the1siteration boundary across orders
(D1/(0,8) thenD2/(4,8)); all receipts remain. No selective repeat or claim of a
deterministic wall-policy result. Twenty-four queries complete31.822s. The
predeclared fresh-input gate passes in both orders on actual loss protection
and additional second-phase time; its6family result is reported below only
after completion.


## Fresh development comparison and actual consequences

The input-only6family protocol was frozen before its outcomes, with a go/no-go
premise from the exposed cap2 mechanism. All144queries/12planned roots complete
in381.095s, no generation failure, replacement or missing slot. Sizes8/12/16,
roots0/8, full generator rules and histories are retained. These are new to this
schedule declaration, not claimed globally untouched or an all-domain holdout.

Across48matched triples, cappedD2and q4choose the same action36times. Neither
loses/gains an actual requested-q completion relative to q4; the oldD16reserve
loses4receipts (5312/8and5322/0,1s, both orders). Crucially, old reserve and
cap2choose the SAME action in all48triples. Recovered policy/depth fields alone
therefore do not establish additional decision benefit. No new immediate-loss
witness is found;13complete no-win scans,1actual child terminal and2UNKNOWNs
retain their separate scopes. All48q4/cap2pairs pass delivery; one old-reserve
call expires. Maximum measured full-return overshoot is.000971s, not suppressed.
Every fresh phase PV contributes522fully checked edges.

A NEW fixed4096node continuation on BOTH actors forces the original transfer's
first choice at three predeclared exposed parents, then uses the same fully
disabled-q policy. Six games close in41.554s;64additional plies/30s per game stay
frozen. The176actual edges are independently replayed with search disabled.

|Parent|q4first choice|Original reserve first choice|
|---|---|---|
|4323/12|actual LOSS,2edges|actual WIN,19edges|
|4322/8|UNKNOWN at65edge cap|actual WIN,37edges|
|4312/8|actual WIN,17edges|actual LOSS,36edges|

The last row is a concrete adverse conditional outcome for the fixedD16reserve,
not just a shallower-depth warning. The cappedD2alternative selects the same
first action as the successful q4branch on4312/8, and the same protected reserve
action on4323/12. Those recorded trajectories are evidence about those actions;
they are not separately executed cap2matches or optimalWDL. At4322the new timed
q4control straddles its completion boundary; original fixed first-action records
remain the continuation inputs. No old experiment is rerun or relabeled.

Decision: reject unconditional adoption of the fixedD16reserve. Keep cappedD2
as a cheaper research candidate with demonstrated exposed-case loss protection,
no global/default change. The small new-family sample supports a cost/coverage
observation, not generalized strength. No larger games or q-parameter sweep is
launched on that basis.

## Separate consumer and next discriminating question

A search-disabled consumer replays all82roots,1320actual phase receipts and3796
PV/fallback edges using the existing Core/compiler plus normal product Native,
including all4actual terminal-tail histories and physical-win/winning-reply
receipts. It closes21.426s. It shares the rule implementation, so it is separate
execution, not independent rules semantics or timing replication. The separate
trajectory consumer closes2.457s/176physical edges. No unchanged Native rebuild
or full product regression is substituted for these new data checks; the last
full2687test qualification belongs to unchanged source baselinea3c4959.

Before another reserve curve, a new source examination has actually begun:
[Schaeffer's history heuristic paper](https://webdocs.cs.ualberta.ca/~jonathan/publications/ai_publications/pami.pdf)
(section3 and interactions) motivates measuring repeated sufficient moves at
interior cutoffs. Current Native source has packed action/side/depth at the
cutoff but no inspected history/killer ordering. Existing state training_trace
omits the cutoff action and full played history, so it cannot supply that
statistic. The next bounded feasibility question is whether repeated actual
cutoff actions justify a tiny per-search ordering probe at all. No history
heuristic code is implemented/adopted, no tree/solver/Session runtime/model/
training work is duplicated, and canonical PV/complete rule history remain
hard constraints. The paper's chess results are not GenericChess evidence.

## Primary literature and the cheaper alternative

[Korf and Chickering (1996)](https://www.maxchickering.com/publications/aij96.pdf),
sections2,5 and9, use principal-leaf expansion and a shallow alpha-beta tree
before selective extension, charging both phases in equal-time comparisons.
Their retained-tree algorithm is different from these independent Native calls;
random-tree/Othello results do not establish GenericChess gains. Source review
finds an existing checked legal `root_order_hint`, which can transfer one reserve
action but no tree/bounds. This suggests at most a tiny declared ordering contrast
on actual displaced cases, rather than implementing a competing selective solver
or reusing bounds across different q objectives. No paper experiment reproduced.

## Collaboration and evidence limits

The complete primary thread adds Dot reply1792073974.887139, explicitly correlated
to PRIMARY-RESERVE-ALLOCATION-20261015. Its actual-retained-policy, budget displacement,
physical-win and full caller-time objections are adopted in this experiment.
Dot read the report/source, did not execute our queries/tests. The original
request association remains receipt-tier, with historical code bytes unverified;
new actual arguments/receipt and correlated reply are preserved privately.
The recovery full19reply auxiliary thread contains Dot's narrow source review of AUX61;
PRIMARY read that exchange, not its293tests/48games or later source. Owner
performance claims remain owner-reported and conditional. No routine reply,
extra worker, automatic merge, role conflict or quantified collaboration speedup.

All technical plans, full rules/roots/phase results, failures and replay sources
are published in the companion archive. Raw Slack/account originals stay ignored;
publication copies exclude personal information/passwords/credentials. Exact
public source enables review, without a Dot acknowledgment or publication gate.

Closing complete20reply auxiliary read adds final owner revision65243286224f37f022824fb4cfdad2bff9fc10c6: reported298tests and888newpolicy games/12717moves, plus unit/horizon sensitivity. PRIMARY read the Slack supplement only; no final source/test/game execution or adoption is claimed. It reports reading our prior context without a rerun; costs remain separate. No new channel roots or primary supplements after the adopted reply.

Focused existing Native goal/cancel/budget/q contracts:56passed. Pytest optional cache write reports Errno13; actual tests and research succeed. The publication invocation disables that optional cache provider. Raw warning stays private and its public copy replaces the personal project path. No security setting change or claim that SAC caused this cache warning.

Archive: `../archive/reserve_allocation_20261015/evidence.zip`, per-member hashes and `replay.py`; complete phase records, rules/roots, protocols, all missing slots, controls and next-source examination. Public-copy replay receipt is recorded after actual execution.

Actual sealed public-copy replay passes103members,82roots/1320phases/3796edges plus176trajectoryedges, search disabled. Exact archiveSHA and actual duration are in `../archive/reserve_allocation_20261015/publication-replay.json`. All owned producers have closed; no final success is inferred from source reading alone.

Post-publication source-export correction: I initially read the internal counter
without checking its exporter, then incorrectly said API `nodes` included qnodes.
It does NOT: exporter subtracts qnodes. The frozen producer's `total_nodes` field
therefore means main-only, not total work. All1044actual caller queries and366
two-phase receipts are now audited in
`data/reserve_node_accounting_correction_20261015.json`: every first phase has
qnodes0, and combined main+q across all phases never exceeds1000000. Hence shared
caps, actions, outcomes and timings are unchanged; only the reported work-total
interpretation was wrong. Original archive/source/rows remain sealed. This is
an explicit correction, not a silent repair/rerun or new Native bug.

The frozen8root cutoff-counter protocol is NOT EXECUTED: source examination
found this accounting error first, and correction took priority. No counter
image or heuristic was built; the next-source question remains begun/unresolved.
