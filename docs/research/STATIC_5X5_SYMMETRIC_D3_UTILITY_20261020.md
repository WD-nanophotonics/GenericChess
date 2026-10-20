# Static versus Unit under symmetric D3 budgets on fresh 5x5 rules — 2026-10-20

## Question and decision rule

The corrected 5x5 candidate96 panel compared static_v2 at D8/8192/0.5s against
fixed D2/32768/0.5s foes. The multi-size D3/D8 work curve used D2 fixed foes
and did not include a dedicated symmetric D3 5x5 panel. This run asks whether
the finite static_v2-versus-Unit candidate contrast remains when candidate and
fixed foe have identical D3/8192-node/0.5-second/q0 limits. It is a changed
resource regime with eight new rule seeds, not a refill or pooling of either
previous panel.

The frozen plan is `data/static_5x5_equal_d3_20261020/plan.json`. It uses seeds
523001–523008, the existing three setup-family schedule, two deterministic
four-ply prefixes per rule, both candidate colors, static_v2 and Unit candidate
checkpoints, and each as an unchanged fixed foe: 128 physical games. Both
candidate and foe use D3, 8192 nodes, 0.5 seconds, q0, TT0 and root-window
pruning disabled. Games stop at 96 candidate plies or a true Core terminal.
Ongoing games remain UNKNOWN; no slot is replaced or imputed. Promotion, drops,
full Session history, repetition and real terminal outcomes are preserved.

Before outcomes, the decision rule was: strictly positive all-slot
static-minus-Unit bounds against both fixed foes retain static_v2 as a viable
candidate for this sampled symmetric-D3 5x5 regime; nonpositive upper bounds
against both de-prioritize it only in this regime; otherwise unresolved. No
result alone changes a global price, default, training target or strength
claim. Expected cost was under four minutes from the prior 128-game 5x5 run;
hard cap was 40 minutes. The actual producer completed in 72.454 seconds.

## Observed results

All128 slots returned:122 reached an actual Core terminal and six reached the
96-candidate-ply horizon as UNKNOWN. There were no unstarted slots and no full
history replay mismatches. The analyzer regenerated every ruleset and exact
four-ply opening from the declared seeds, compared the serialized root states,
recomputed and matched all eight static profiles, then replayed all128 records.
Across 4,351 search queries there were 3,023 completed iterations and 1,328
node-budget stops, zero fallback queries, zero qnodes, and no depth, node or
wall-time cap overruns. Maximum caller time was 0.0392 seconds; total producer
wall time includes generation, compilation and serialization. Search used the
Native semantic engine path; the exact extension build/version and capability
counters were not stored, so this is not a provider-version comparison.

The candidate-relative contrast pairs static and Unit candidate outcomes on
the same rule, prefix, fixed foe and candidate owner. Each UNKNOWN candidate
outcome is independently bounded by [-1,+1] before differencing. Conservative
all-slot bounds were:

| Fixed foe | Pairs | Finite pairs | UNKNOWN pairs | Finite-pair mean | All-slot lower–upper |
|---|---:|---:|---:|---:|---:|
| Unit | 32 | 30 | 2 | +0.5333 | [+0.3750,+0.5000] |
| static_v2 | 32 | 28 | 4 | +0.4286 | [+0.3125,+0.5625] |

Both color strata were positive against each fixed foe. Against Unit, owner-0
and owner-1 all-slot bounds were [+0.5000,+0.6250] and [+0.2500,+0.3750].
Against static_v2 they were [+0.2500,+0.5000] and [+0.3750,+0.6250]. A
post-hoc leave-one-rule-seed-out check retained positive lower bounds for every
omission (minimum +0.2857 against Unit and +0.2143 against static_v2). This is
descriptive sensitivity, not a confidence interval or population guarantee.
Seed523002 was adverse or tied ([-0.5,0]) against each foe; several other
seed-level bounds were zero. Preserve this heterogeneity.

At first candidate decisions with identical state hashes, static and Unit chose
different actions in 13/30 root-owner contexts against the static foe and
15/30 against the Unit foe. This confirms the candidate changes choices in
these roots; action differences alone are not utility evidence. Played paths
included 1,191 drops and 270 promotions. The new generated profiles had 32
non-anchor entries in 24 exact movement-signature classes; one promotable
cross-rule pair (523001:P, 523005:B) shared a signature and had identical
raw/normalized values. This single pair is descriptive only and does not
establish cross-rule transfer.

## Interpretation

The prespecified criterion is met: static_v2 retained positive conservative
finite utility against both fixed foes and both candidate colors at symmetric
D3 budgets in this finite generated 5x5 panel. Together with the previous
D8-candidate 5x5 panel, this shows that the earlier 5x5 result was not observed
only under a deeper candidate than foe. It does not override the existing
D3/D8 reversal against Unit in the multi-size work curve, establish a universal
price vector or population effect, or prove a causal leaf-price-only effect:
the current evaluator also supplies price-dependent capture ordering. Keep
static_v2 as a cheap candidate/baseline; do not activate it as a global
default. Do not enlarge the 5x5 panel without a changed decision or consumer.

Read-only replay and audit:

```powershell
.\.venv\Scripts\python.exe docs/research/data/static_5x5_equal_d3_20261020/analyze.py
```

The analyzer verifies generator seeds, exact opening actions/root hashes,
profiles, planned-slot identities, actual outcomes, search caps and full Core
history replay without launching searches. The producer source, plan, profile
hashes, tracked Python-tree hash and pre-run tracked-diff hash are in
`data/static_5x5_equal_d3_20261020/producer-source.json`. Do not rerun the
producer in this frozen evidence directory: it overwrites the records.
