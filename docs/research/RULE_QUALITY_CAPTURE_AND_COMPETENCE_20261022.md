# Rule quality, capture mechanisms and finite competence — 2026-10-22

The new generated-rule grid supports two **finite policy improvements**, but
neither raw branching, shorter inventory nor nominal search depth is a reliable
quality verdict. Keep the opening-win preference optional and the generator,
search and learning defaults unchanged. The strongest new mechanism result is a
fully legal history counterfactual: the same two-king board is in a restricted
no-mate class after capture removal, while restored captured stock permits a
Core-verified win in three plies. This is a change of rule and resulting reserves,
not a same-RuleSet board-only value impossibility theorem.

## Why this question and what changed

The 09:48/09:58 JST incoming Chat comments propose independent research on rule
quality instead of further low-yield service-cost work. Adopt that existing-scope
question; do not treat comments as new authority or take over DEV_AUX's learner,
graph or solver. The prepared fallback/evaluator96-game task stays **NOT RUN**.
Read-only Chat originals and full threads were saved privately before assessment.

First reuse all72 existing full histories. Original512-ply rules have30 mates and
6 caller-censored games; the separate, genuinely different24/48-ply rules have
24 mates and12 actual MAX_PLY draws. These cohorts are not matched clocks, a new
filter comparison or independent role samples. Their original outcomes remain.

A frozen pilot makes8 generator calls, all successful, and32 initial-state
D1/D2 q0 evaluations:1,190 Player returns,35.919s. D2 wins15 of16 mixed-role
matches. Only5 complete rules underlie the8 intention slots: three flag pairs
accept the same rule. No population confidence or learning conclusion follows.

## A depth label does not define a strategy ladder

On those same8 slots, a separately frozen random-four-ply opening retains all
history and stops at real terminals. The common-q4 D3/D2 comparison has32
continuation evaluations,808 new queries,563.242s; four starts are already
terminal and make zero queries. Its deeper-policy finite utility interval is
[-1/2,-1/4]. RequestedD3 includes193 completedD3 returns,117 D2 returns,103 D1q0
reserves and10 immediate wins. The result is neither solely failure to reach
D3 nor a general search-pathology theorem.

Complete the missing rung on **exactly the same** q4/prefix inputs:24 new
continuation evaluations,379 queries,97.920s, plus8 exact existing D2/D2 receipt
reuses. Three new evaluations have terminal prefixes. D2/D1 is5/8 while D3/D2 is
negative. These fixed algorithms do not form a monotone skill chain. A posthoc
four-run common-tail intervention at the first actual divergence pays95 queries:
the two first choices differ under a commonD1 tail but not under a commonD2 tail.
This is conditional policy interaction, not perfect-play action WDL.

Lantz et al. distinguish meaningful choices from raw branching and define a
resource-dependent ladder over strong strategies; they do not supply a universal
quality threshold. Our capped AlphaBeta variants are not optimal algorithms for
their resource levels, and two positive rungs would not establish that formal
property. [Depth in Strategic Games](https://www.nealen.net/papers/Lantz2017Depth.pdf).

The existing terminal-only D4/256-node probe returns UNKNOWN on all30 available
predeclared prefix observations, even one with a separately known one-ply win.
Some histories are absent after actual game end. This is an incomplete probe,
not proof of absent choices and not a gate requiring complete WDL before work.

## Fresh rules and the opening preference

After the cost preflight, fix12 new seed/condition blocks:4/6/8 boards, classic
or free-random setup, bilateral or unrestricted movement; both preference flags.
All full future types, promotion/drop declarations and history remain. There are
24 actual generation calls,22 successes and2 bounded16-attempt refusals, both in
one4-board free-random block. No replacement or cap extension. Capture-rule
counterparts below are interventions on these inputs, not extra generation.

Common q4 D1/D2,8192 total nodes and1s per query,96 caller plies and a3600s whole
cap produce88 games,3,065 queries and1,257.135s. Eight planned games are unavailable
through generation refusal. Keep actual result source, completed depth, timing,
fallback and operational masks. No fallback is silently promoted to eligible.

| New-grid contrast | Planned-completion sensitivity | Accepted-input conditional interval |
| --- | --- | --- |
| D1 versus uniform legal | [3/4,1] | separate44-game conditional data |
| D2 versus D1 | [1/6,1/2] | [3/11,5/11] |
| Opening preference on minus off, D2 step | [-1/3,1/3] | [-2/11,2/11] on11 both-success pairs |

These are finite censoring/completion bounds, **not sampling confidence intervals**.
A refused generation has no observed game; its planned-completion endpoint is a
sensitivity calculation, not an invented latent draw or an assumption of yield.
The low rung executes44 actual games:42 D1 wins,2 UNKNOWN,571 search returns and
551 separately recorded uniform choices,25.512s. Four slots are unavailable.

Nine both-success preference pairs accept identical complete rules; two replace
them. In both replacements, the observed D2/D1 contrast stays0 and the first
player wins both D1 and D2 self-play, despite removing the one-ply opening win.
There is no demonstrated additional skill/balance benefit of the preference on
this grid. This does not refute its narrower opening-pathology purpose.

## Capture removal is not an automatic playability improvement

Change **only** capture_disposition to remove_from_game on each accepted input.
Every other RuleSet field, including512 rule plies, declared promotion/drop and
future types, stays. Initial positions differ strictly in their necessary rule
fingerprints; every other position field, initial legal action and board price
is checked equal. Preserve the original strict-false receipt and its causal
diagnosis. These are new rules, never replacements for old censored games.

The counterpart executes88 games,4,310 queries,492.056s within its1800s cap.
There are16 actual rule draws and25 raw UNKNOWN versus0 and10 in the pocket
cohort. Its D2/D1 planned interval is[1/6,19/24]; remove-minus-pocket sensitivity
[-1/3,5/8] identifies no robust competence improvement. Different accepted rules,
policies, completed depths and clocks must not be collapsed into a speed claim.

Uniform-legal streams use four predeclared paired seeds per rule, swapping streams
between seats. Each variant has176 recorded views but only104 executed unique
games;72 same-full-rule/stream views are exact reuses. Sixteen intended views are
unavailable in each variant. Reconstruct every unique history and exact RNG
choice sequence, and check complete RuleSet equality before counting a reuse.

| Random-policy outcome views | Capture to hand | Remove from game |
| --- | ---: | ---: |
| Checkmate | 48 | 14 |
| Actual stalemate draw | 12 | 20 |
| Actual repetition draw | 0 | 2 |
| Caller-censored ongoing | 116 | 140 |

Both use the same96 observation cap. Common seeds do not guarantee the same
states after legal frontiers diverge. Random-policy censoring grows even while
inventory can shrink; D1 still beats uniform on the original rules. This separates
policy-dependent observation from intrinsic absence of strategic possibility.
Browne and Maire's self-play quality criteria are useful hypotheses rather than
canonical admission labels. Their treatment of abandoned trials is not imported:
our cutoffs stay UNKNOWN. [Evolutionary Game Design](https://rafal.io/static/papers/evolutionary_game_design_ludi.pdf).

## A restricted closed class and a real stock-enabled win

Eighteen remove-mode final views,9 unique, have only one unpromoted K
anchor per side, no hand or auxiliary state. The source-assisted argument checks
all conditions: identical8-adjacent leaps, anchors uncapturable and safety-checked,
no K promotion, custom creation/actions, declarations, automatic/consecutive/
cycle-loss adjudication or pass; repetition and stalemate draw; finite512 clock.

A legal king move cannot give check: adjacency would put its own king under the
same symmetric attack. Empty hands and no ordinary actors preserve the class;
there can be no future mate. All permitted endings are draws and the finite
clock terminates play. This is a conditional inductive argument supported by
all82 legal one-step edges of the retained views, not an exhaustive graph or a
new solver. **The raw96-ply UNKNOWN records remain unchanged.**

Replay those same actual action sequences legally under the original pocket
rule, changing only the record's required rule fingerprint. All18 views/9 unique
replays pass: identical board/side/aux/shape, with legitimate captured stock and
588 available stock-drop views; there is no immediate winning child. No pieces
are inserted into an arbitrary position. Different rule/history/reserve contexts
mean this is not hand-only causal identification inside one fixed RuleSet.

A predeclared existential check considers53 checking drops on the9 unique
counterfactuals, using the existing bounded probe. It stops after6 returns when
one win-in-three is found;47 remain unattempted, not failed. A separate Core reader
checks **both** legal opponent replies and a literal terminal mating response to
each. The first move is P@c3 in the4-board seed202610221200 case. This demonstrates
more than extra branching: the legally reconstructed stock supports a real win.
No oracle label is supplied to training.

Two new rule-goal boundary controls replay the same legal history. A valid
zero-threshold declaration permits WIN; an automatic adjudication yields
NO_CONTEST. The closed-class preconditions reject both. Do not generalize the
restricted draw claim to the complete generated/semantic rule domain.

Six cold-player recognition queries retain all actual outputs. In the pocket
WIN, default q4 completesD1; requestedD2/D3 time-limit back toD1. Its chosen P@a4
has neither a mate3 certificate nor an opponent immediate winning reply; its WDL
is **unknown**, not a proven error. On remove DRAW, D1/D2/D3 complete and return
heuristic21; that score is not WDL. One separately frozen q0D3 control completes
in the same8192-node/1s envelope, returns the winning P@c3 and passes its own
all-reply mate3 check. One exposed state warrants no q/default activation.

## Product repair, validation and reproducibility

Actual quality-metric failures are reproduced before repair: CENSORED/UNRESOLVED
counted as short terminals; decisive stalemate/perpetual check counted as draws;
MAX_PLY/no-progress/action-class draws omitted; an unrelated passing threshold
promoted another flag that failed its own threshold. Eight captured red cases
support the causal repair. All original assertions remain. Optional winner and
outcome-aware draw fields preserve old positional constructors, and old profiles
without winner counts use conservative unambiguous draw statuses. NO_CONTEST
has no reward. No default admission thresholds are introduced.

All **3,655 active-layer tests pass**,0 failures/errors/skips. All completed game
histories and literal returned PVs use the full shared Core; this is not an
independent rules implementation or certification of every unseen q tail. Reader
input-path and compilation-representation errors were preserved, diagnosed and
repaired without replaying producers or altering actions. One q0 preparation
syntax error occurred before any query. Every scientific return is retained.

The exact technical [capsule and summaries](data/rule_quality_and_capture_20261022)
contain full inputs, results, failures, witnesses and the newly used harness
sources once, with member hashes and sanitized publication copies. File-byte hash references
are translated consistently to those copies, with all private-original identities
retained in the manifest. Public members pass33 unique RuleSet and470 canonical
GameRecord parses; extracted random/Core proof readers also run before delivery. Private raw
Chat/account/test logs stay ignored; no full vendor/source-tree dump is added.
Existing published AUXd485c487 Leaper conclusions inform scope only; PRIMARY
neither executes its graph/learner nor writes its checkout. No outbound message.

Next: the complete fixed-prefix catalog and24 actual canonical preflight inputs
are prepared. Estimate cost before stratifying existing experience into immediate
win opportunities, the restricted closed class and remaining UNKNOWN. All follow-up
queries are **NOT RUN**. Continue rule quality without oracle-selected training,
a new solver, another blanket50-rule survey or a default filter. Science OPEN.
