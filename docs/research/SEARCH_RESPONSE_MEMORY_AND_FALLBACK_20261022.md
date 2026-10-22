# Response memory, root allocation and incomplete fallbacks — 2026-10-22

PRIMARY_SANDBOX session `e2250de6-b736-475c-8a97-462b49b56933` records
3,750 effective seconds (62m30s), eleven actual intervals. Recovery, transport,
the rejected product migration restore and delivery are excluded. Science OPEN.

The main result is a useful but narrowly scoped fallback-policy candidate,
not a default change. The existing public canonical no-scan fallback contract
is preserved. Production search, evaluator, Native admission, TT/history keys,
learner, AUX checkout and recurrence are unchanged. The maintained cost CLI
only exposes the already-existing `--countermove` switch, default OFF.

## Existing response memory and a new primary-source check

[Uiterwijk's original countermove paper](https://journals.sagepub.com/doi/10.3233/ICG-1992-15103)
motivates testing whether a previous action predicts a useful reply. Its chess
results are not transferred to this generated-rule domain.

Freeze eighteen new mixed-rule configurations across 4/6/8 boards, three setups
and two symmetry modes, with the existing optional no-opening-win-in-one
preference. All generate successfully. One naturally unavailable later prefix
leaves 35 available roots from 36 targets: 420 actual queries, with all 216
planned processes executed. Missing natural-terminal slots remain explicit.

A four-cell countermove/staged-ordering factorial requests D3/D4/D5 under the
same complete roots, default evaluator, q0 and resource limits. Matching full
horizon scores/actions agree. Counter/base cold setup-plus-query medians are
0.9947, 1.0124 and 0.9936; all fail the declared 20% cost gate. Counter added to
staging also fails. There is no new utility campaign or default activation.
Core replays 1,425 literal PV plies and 2,448 root-history plies.

Separate instrumentation finds 12,015 legal counter occurrences but only 94
actual changed full-sort orders across five roots. There are 117 cross-side
writes, but no observed cross-side legal response. This is ordering information,
not evidence of semantic cache corruption or a reason for a new key API.
Five original diagnostic calls failed when the recorder tried to serialize a
mutable runtime view. Their failures remain; only these five diagnostics rerun
into separate records using immutable position snapshots. No cost/game panel
was replayed, and instrumented times are not speed evidence.

[Schaeffer and Plaat's primary paper](https://liacs.leidenuniv.nl/~plaata1/papers/acm-final.pdf)
suggests a different cheap experiment: repeated zero-window bounds with memory
and a previous-iteration guess. A private wrapper uses the existing negamax,
full history identity and TT; both arms require a full executable PV. No new
search kernel, forward pruning, table or product API is introduced.

All 140 queries execute. Matched D3/D4 values agree; full caller median costs
are 2.223/2.569 times the full-window baseline, with nine lost D4 completions.
An optimistic subtraction of all PV reconstruction cost still gives 1.130/1.243.
Thus a reconstruction rewrite alone cannot meet the gate on this measured work.
The current table stores one bound per entry; this does not refute other MTD
implementations. Literal Core PV checks cover 442 plies.

A further 140-query exact leaf-scale counterfactual fixes ordering and compares
factors 1 and 3. All 70 pairs are unclipped and preserve nodes, pass structure,
actions, PVs and the expected score mapping; Core checks 400 PV plies. Wide
integer grain therefore does not explain this observed fail-soft overhead.
No price normalizer follows. Separately, even making the entire default evaluator
free would give median fixed-work caller ratios 0.831/0.901/0.915 at D3/D4/D5;
a material-only rewrite is not a justified next engineering step here.

## Root pre-scan: resource relief is not utility

A new eighteen-rule, both-role comparison changes only the existing root tactical
scan switch against a fixed default opponent. D3/q4, 4,096 nodes, 1 second,
96 caller plies and a 1,800-second whole cap are frozen before generation.
All 36 games execute in 1,070.85 seconds, paying 1,436 queries. Actual results
are 15 wins, 15 losses and six UNKNOWN, giving finite **[-1/6, 1/6]** against
the analytically balanced SAME-control selfplay aggregate zero. No redundant
control selfplays are executed. Sixteen role pairs have identical observed
trajectories; this does not link their unknown future outcomes.

Full Core qualification covers all 36 final states/histories and 2,849 literal
PV plies. Phase-specific root-scan time is not exposed in PlayerDecision and
remains unknown, not zero. No root-scan default is changed.

Another 348 calls compare tight budgets on 58 complete semantic roots: rectangular,
future-type, promotion/drop and actual token branches remain. An explicit complete
Unit evaluator uses CURRENT board 1000 / BASE hand 900, metadata anchors zero,
with dynamics off. There are 216 requests with an actual available Native provider;
other admission paths remain Core. All returned fields and 447 Core PV plies stay.

At budgets 16/64/256, ordinary fallback counts change from 47/9/0 with scanning
to 33/2/0 without. Matching returned-policy scores agree. Proved wins are kept
separate from completed depth: an immediate proof at depth zero is not inferior
to a later completed iteration. These are resource diagnostics, not game utility.

A separate prospective clock sensitivity uses nine NEW base configurations and
changes only the actual rule max_ply to 24 or 48 before any search. All other
rule fields match and full fingerprints differ. The 36 games pay 808 queries;
Core checks every final history and 1,348 PV plies. The 24-clock group has
12 actual MAX_PLY draws and six mates; the 48-clock group has eighteen mates.
Both finite contrasts and the clock interaction are exactly zero. These new
rule outcomes do not turn any original 512-ply-rule UNKNOWN into a draw.

## Actual auxiliary changes as an additional q signal

A private prototype adds the complete auxiliary tuple to the existing parent/
child inventory equality test. Legal actions, prices and history are unchanged;
this changes selective q inclusion, not Core rules. The 152 calls cover 58
semantic roots plus eighteen empty-aux generated initial-root controls.

Nine roots have quiet auxiliary-changing actions. Four real token states actually
exercise the altered q frontier, adding four to six qnodes, with unchanged
returned choices/scores. The 56 matching full-D2q4 semantic pairs have no choice
or score change; ten complete empty-aux controls agree too. Core checks 282 PV
plies. Incomplete control counter differences are clock/load censoring, not
auxiliary activation. No product toggle/default follows. Candidate raw
material_change_qactions includes the experimental aux marker and must not be
interpreted as physical material change. Q search remains explicitly selective.

## Reusing already-paid incomplete first-iteration work

An actual no-scan, node-16 semantic query returns a canonical king move, whereas
scanning retains an off-target capture as fallback. The completed-root-win path
already works before a full iteration; no duplicate win mechanism is needed.
The new question is reuse of nonterminal completed first-iteration children.

A private q0/hard0 observer retains the best actually completed D1 child. Only
an ACTION legal_fallback can substitute its action; score zero, empty PV,
completed depth zero, actual stop reason and fallback source remain. Declaration,
proved win and completed-iteration choices are never replaced. No evaluation,
transition or node is added. This is a new policy diagnostic, not a claim of a
completed search or generic q4 correctness.

All 608 calls execute on 76 full roots. All 304 pairs have identical paid
nodes/qnodes/evaluations. Among matched fallback pairs, selected true complete
Core D1 values improve in 18/15/5 cases at budgets 8/16/32; none worsen here.
Those finite leaf comparisons do not guarantee WDL or unseen-action dominance.
Core checks all returned choices and 666 literal PV plies.

Before new games, explicitly define an **intentional fallback-policy task**.
Twelve NEW base rules have a genuine 48-ply clock; 16/64-node tasks both face the
SAME fixed no-scan lexical Unit opponent. The new task accepts its expected
node-limit legal_fallback as policy output, while operational errors, invalid
time, illegal choices or missing outcomes remain UNKNOWN. Existing ordinary
runner eligibility and utility intervals are retained UNCHANGED beside the
separate preregistered policy-task masks. This is not a reinterpretation of any
previous benchmark or ordinary completed-search strength claim.

| Nodes | Actual games | Policy-task W/L/D | Policy-task finite contrast | Ordinary benchmark interval |
|---|---:|---:|---:|---:|
|16|24|8/7/9|1/24|[-11/12, 11/12]|
|64|24|8/6/10|1/12|[-5/12, 5/12]|

These are twelve exposed rules and finite contrasts, not independent population
estimates or Elo. There are 24 generation calls but only twelve distinct base
fingerprints, not 24 independent rules. All 48 games finish in 29.81 seconds,
paying 1,293 queries. Core qualifies full final states/history and 1,002 PV plies,
then independently verifies all 1,077 retained child values and 173 substitutions.

A narrow product attempt reproduces four real legacy lost-fallback regressions.
Its first new semantic fixture assertion was overbroad: semantic pattern IDs
already put that capture first. The actual Core frontier explains this; the
initial failed evidence remains. No old numeric expectation was changed.
The attempted implementation then hits an EXISTING explicit test requiring
canonical first fallback when root scanning is disabled. That is a caller
contract, not a stale number. The small intentional-policy result and absence
of a concrete consumer migration do not justify overriding it or adding a flag.
The exact parent product search and assertion file are restored; the candidate
patch is evidence only and is NOT DEPLOYED. Current default behavior is preserved.

## Next step actually begun; delivery limits

The next discriminator keeps the SAME Unit lexical foe and completes C/D of an
evaluator/fallback four-cell contrast: default evaluator lexical/partial against
that foe. This prevents changing both sides and miscalling the result an isolated
interaction. Twelve complete default/Unit profiles and full fixed inputs have
actually been constructed and saved. The 96 new C/D games are **NOT RUN**.
Report D-C and (D-C)-(B-A), all family pairs, masks and costs if pursued. This is
an exposed development comparison, not a holdout, learner or AUX assignment.

The latest published AUX report is read only at
[d485c487](https://github.com/WD-nanophotonics/GenericChess/blob/d485c487ba6c3503a7d5af9d8bba465746dfb9a1/docs/research/LOCAL_MAINLINE.md):
its deeper unsafe ties support caution about depth as a proxy. No AUX program,
training, solver, checkout or unpublished work is executed or modified.
The once-per-patrol incoming Chat read has no new roots/replies; exact reads stay
private. No outbound messages, worker, schedule or visibility changes occur.

[Compact summary, full technical packet and source](data/response_memory_fallback_20261022/README.md)
retain 5,345 planned-study query returns, plus forty instrumented diagnostic
attempts with the five original failures and repaired calls distinguished.
Core qualification covers **8,861 literal PV plies**, not unseen q tails or an
independent rules engine. Two exploratory fixture calls retained only compact
console observations rather than full decisions; they are excluded from scientific
counts/claims. One initially attacked-anchor fixture fails before any query.

All 425 packet members parse/compile as appropriate and have hashes/CRC; source
is stored once. Private absolute paths are sanitized only in publication copies;
private originals/hashes stay. No raw Chat/account/pytest logs or credentials are
published. The initial 70 affected checks passed. The prescribed publication gate
reruns the affected targets; its result and full remote SHA are delivery evidence.
The parent 3,616-test suite is prior evidence, not a newly rerun suite. Science OPEN.
