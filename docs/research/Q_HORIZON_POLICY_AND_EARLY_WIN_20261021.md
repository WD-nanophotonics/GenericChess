# Q horizons, actual policy utility and optional early wins

2026-10-21, PRIMARY_SANDBOX. Science remains open. Evidence is in
[data/q_horizon_20261021/summary.json](data/q_horizon_20261021/summary.json).
Its source hashes identify the exact private originals; full rules/records and
explicit Core certificates are retained where needed, without publishing raw
Chat/account outputs. The prior four-rule inputs remain in the referenced
semantic_probe packet at bffe1e4b5f0a98ca6215eae3b83b329962db37db.

## Decision and implementation

Added `SearchTuning(stop_after_root_win=True)`, default **False**, for callers
whose objective is any completed winning root child. It reuses the existing
completed-child result, checks cancellation/deadline before returning, and
reports `root_win_found`. It does not promise shortest mate, a completed whole
iteration, or a literal full winning PV. Completed depth remains actual (even
zero); incomplete-iteration wins use `completed_root_win`. Compatible warm exact
root returns also stop without starting another iteration. Their existing TT
policy/provenance limitations remain. Arbitrarily large static scores cannot
supply a mate claim. No Native C, generator default, evaluator default, learner,
UI or AUX change.

The maintained `scripts/semantic_probe_cost.py` exposes this option, optional
existing no-opening-win-in-one sampling, attack-evaluator backend controls and
rule setup timing. Its successful execution path is unchanged apart from these
explicit options. An executed query is now saved before a replay qualification
failure is propagated; a controlled failure and a zero-node success smoke verify
both paths. Defaults, existing result fields and import paths remain.

## Utility before speed

On four exposed hybrid rules/eight full histories, q1 gives fourteen D2
completions plus two immediate wins under 5000 nodes/1.25 seconds. This alone is
not utility. A separately frozen, shuffled 32-game panel compares D2q1 and D2q4
against the same D2q0 opponent, 5000 nodes/.2 seconds per query, 48 additional
observation plies, preserving actual rule caps:

| Candidate | Win | Loss | UNKNOWN |
| --- | ---: | ---: | ---: |
| q1 | 2 | 6 | 8 |
| q4 | 1 | 9 | 6 |

All32 slots ran. One q1 query took .206438 seconds and fails the .205 tolerance;
retain that unqualified slot. Paired utility is only identified within
[-0.625,1.125], not a confidence interval or robust gain. Fresh public Core
replay verified922 additional action edges and complete initial histories.
Twenty-four observed mate-band claims agree with subsequent observed play;
that follow-through is not an all-defense proof.

On one finite3x3/max-ply6 game and its equivalent rewrite, actual unfitted search
has two D2q0 WDL mistakes per encoding across101 cold roots. D2q1, D2q4 and D3q0
have none. Actual persistent-player continuations from all101 roots, four modes,
two encodings give808 conditional starts: q0 has ten wrong starting-context
values; other modes have zero. Paid nodes are3056/3868/4072/4742 respectively.
Opening q0 draws an exact win; q1/q4/D3 win. Exact labels assess, never fit, the
rule-derived evaluator. These starts are correlated and the encodings are one
game, not two independent families or generic strength evidence.

Separate exposed-label analysis constructs a position-only oracle optimal
policy on this finite domain:67 positions cover101 histories. Clock aliases
also share an optimal action. Neither finding proves that history is generally
unnecessary; neither is a learned or held-out player. Do not conflate these
oracle certificates with the actual unfitted search experiment.

## Screening use and correctness

Sixty-four fixed new hybrid seeds (2026102161..2026102224) use the existing
optional no-opening-win-in-one preference, D2q1,4096 nodes/.5 seconds. All64
slots generated/ran:50 whole D2 completions,14 time limits, six mate3 flags,
three of them completed-child wins from an incomplete whole iteration. Six
independent explicit public Core all-defense certificates prove those flags.
The other58 are not proved nontrivial. Generation/compilation6.145s, player
setup .835s, queries19.688s, total31.794s; recording/control is not free.
This preference changes the accepted-rule distribution.

An interleaved128-query paired prototype retains the exact six classifications
and certified actions, flagged query-time ratio .62243 and aggregate .96174.
It passes its declared cost checkpoints. Actual production-flag qualification
on those same64 inputs returns47 completed-depth, six root-win-found and eleven
time-limit results, with no fallback. This supports the small opt-in feature,
not a search default, uniform horizon or mate-distance claim.

A separate predeclared extra-budget curve on all eleven unresolved nonmate cases
uses16384 nodes/1.25 seconds. Two additional mate3 wins receive independent Core
certificates; one remains time-censored. The extra8.225 query seconds and two
flags are not inserted into the original64 results. Same-total-budget staged
player reuse on those eleven inputs preserves decisions but adds1408 nodes and
cost ratio1.03963; no scheduler is adopted.

Two real role1 winning positions stop at completed depth0 when appropriate.
Promotion/drop/auxiliary-history fixture roots at plies4/6 have independently
certified wins; their root moves are quiet, not promotions/drops. At ply5,
nonwinning action/score/PV/work remains identical. Full parent states/histories
are restored. Do not misattribute the D2q1 versus prior D1 horizon difference
to the new early-stop option.

## Alternatives and limitations

Native attack evaluation matches315 qualified states but offers small,
noninterleaved timing differences. An empty-aux hash prototype gives .96607
median cost ratio, failing its <=.95 checkpoint. Neither is adopted. Half-budget
q1-then-q4 reserves duplicate work and do not resolve two complex cases. Preserve
these negative findings rather than adding another controller.

Clune's full2007 paper models payoff, control and termination, and its stability
ratio includes total variance as well as adjacent change; stability alone is
not that method. A full generic port is deferred, not refuted.
[Primary paper](https://cdn.aaai.org/AAAI/2007/AAAI07-180.pdf).
Ye/Marsland's search experiments separate ordering/cache and selective-search
cost/risk; equal values, paid work and actual utility remain distinct here.
[Author-hosted paper](https://webdocs.cs.ualberta.ca/~tony/RecentPapers/Experiments-FP-YeMars-1992.pdf).
No human price/holdout fitting or new learner was performed.

## Validation, failures and next decision

The full four-layer suite passed3583 cases. Two subsequently added oversized
static-score cases passed separately; this is not a claimed3585-case full run.
The required publication gate reruns current affected contracts. New tests first
failed before the option existed. One new declaration test assumed a node-limit
exit although early success uses13 nodes under a14 cap; diagnosed the boundary
before correcting only the new-mode assertion. Another new mock omitted the
ordering interface; its isolated test disables ordering. Old expectations remain.

A separate16-slot Core-bound diagnostic lost its first executed measurement to
a caller dict/attribute error;15 retained, no replacement cost slot. A first
mixed-lifecycle assertion incorrectly assumed no winning score at the changed
horizon; corrected after explicit terminal certification. Private Chat save hit
Windows command-length206; the same retained response was saved in chunks,
without rereading or dropping messages. These are actual failures, not successes.

Next, test D3q0 as a new16-slot fixed-opponent arm at the same5000 nodes/.2s and
48 observation plies (300s/4M total). Eight actual preflight queries already show
four changed actions, but no outcome evidence yet. Never refill old UNKNOWN.
Keep q1/q4 and static/learned alternatives; no default or scientific objective
is closed by this segment. Additional raw diagnostics remain ignored locally;
this compact packet is the supported publication record, not a promise that
all exploratory one-off producers are maintained executable entry points.

Publication-copy validation separately replayed all32 hybrid games and808 finite
outcome links (130 distinct world/records). Two read-only validation callers
first used a nonexistent Session.terminal method and a legacy compiler on
explicit semantic rules; corrected to terminal_result and compile_semantic_ruleset.
No rule guard, expected outcome or product code was weakened.
