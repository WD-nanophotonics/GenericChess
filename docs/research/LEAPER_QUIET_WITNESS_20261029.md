# One legal quiet-coverage witness; no Q policy change

Status: CLOSED, NO_GO for changing the current Q policy from this candidate.
This is PRIMARY_SANDBOX research on pure Leapers, not a new solver or a strength trial.

## What changed the judgment

The first predeclared source-attributed witness is H6 index1841, family5,
`cd4e7885613c60ac9bd51367e907fd9975b092c2948cfee5a8f6b7b63397ceb1`.
Its full RuleSet fingerprint is
`8cfd27c16ca68171dd03912f067b3f7e4103ea4a1dfd3e2deece2a4921fe113c`.
The original3x3 rule, ply0, max-ply6, repetition2 and complete setup/record are
preserved. Root side0 is not in check. All four legal actions match the published
source labels and current Core classification:

| A from(0,0) to | Kind | Source WDL for root side0 |
|---|---|---|
| (2,0), g10 | quiet | DRAW [0,0] |
| (2,2), g11 | noisy | LOSS [-1,-1] |
| (0,1), g6 | quiet | LOSS [-1,-1] |
| (0,2), g7 | noisy | LOSS [-1,-1] |

These labels come from AUX's published H6 packet at
[5584387c](https://github.com/WD-nanophotonics/GenericChess/tree/5584387c8de5b23a3b1524cce9c29bd694bee2d8/docs/research/data/leaper_h6_initial_truth_20261023).
They were not independently solved here. Source input/truth SHA256s are
`75ce22f0ce2b4bc522a8f1e0149d5e68a138eefc45468068779e84146720956b`
and `56e720c681c4417693758a777c6625485c6fd330f283242c74442c9440a1911c`.
The ordered scan visited1842 source roots and made323 Core child transitions,
stopping at its FIRST strict nonempty quiet/noisy contrast. This is not H96,
a holdout, or proof of a service-controller error.

## Actual returns and dependencies

Default raw stand-pat is -174. Wide-window Q4 returns -174; the observer sees both
quiet actions actually classified and skipped, then a return supported by
stand-pat. Adding quiet while retaining stand-pat still returns -174. Forcing
one root legal step over ALL actions also returns -174, from g10. Forcing only
noisy actions without stand-pat returns -999999998. Forced controls explicitly
spend one additional root step, including the manual first-Q0 context; their
recursive children retain production Q. They are not a product feature.

At window[-176,-175], stand-pat returns a LOWER bound before legal generation.
At[-73,+INF], the return -73 is inherited alpha and an UPPER bound, not a leaf
value. Child bounds are negated with UPPER/LOWER reversal. TT is disabled in these
scalar contexts; no cross-policy numerical reuse is assumed.

All eight cold current-main calls (D1,D2,D4,D6, two manual first-iteration phases)
already choose source-DRAW g10. D6 returns0. Changing depth/phase changes numbers,
not the chosen action here. Thus coverage importance is real, but neither a
stand-pat-induced root error nor the cause of an old service-root flip is shown.

Twenty-three of24 original counterfactual slots have saved results. The first
Q0-wide baseline slot failed a consumer assertion: RuntimeSearchState is a view,
not a GameState dataclass. Its numerical original was not saved and remains
UNKNOWN; it was NOT replaced. The remaining23 used the corrected full-position/
history rollback comparison. A later audit also fixed a method-vs-value search-key
snapshot bug; the three observer calls explicitly validate actual search_key().
Executed source versions and diagnoses remain literal archive members.

## Controls and verification

Sixteen follow-up cold scalar results and all23 retained counterfactual returns
match an immutable GameSession/Core execution route (39 checks). This shares
search/evaluator code, so it is not an independent implementation or WDL proof.
Three AST return/classification observations match original scores, nodes,
Qnodes and evaluation counts without extra generation/evaluation.

A separate ARTIFICIAL tree uses stand-pat+2, quiet continuation0 and noisy-1.
Wide returns are old/+quiet=2, no-standpat/noisy=-1, forced-all=0. With an artificial
parent competitor-1 this changes an exact parent choice; an inherited-alpha
bound at[1,3] instead overlaps that competitor and cannot certify a flip.
Production Q code is checked on84 integer-window/policy combinations, with no
claim that the synthetic tree is a legal Core position or the actual H6 cause.

The strict witness consumer now compares quiet LOWER against every noisy UPPER;
UNKNOWN noisy labels cannot establish dominance. The original admitted labels
were exact, so this consumer repair does not alter the executed selection.
No failed older H96 certificate, clock panel or nine-root Player panel was refilled.

## Evidence and consequence

[Manifest](data/leaper_quiet_witness_20261029/manifest.json) binds32 literal members
in bundle.json.gz, including frozen plans, failures, raw returns, current Core
records, source versions and observer sites. Decode each member.text as UTF8
without newline conversion and verify its SHA256. candidate.json.gz is a small
separate fixture for current tests. Raw/enriched duplicates are not extra calls.

Keep Q unchanged. The cost alternatives and current direction are documented in
[the static-evaluation assessment](LEAPER_STATIC_EVAL_20261029.md) and
[the next protocol draft](LEAPER_THREAT_ORDER_PROTOCOL_20261029.md).
