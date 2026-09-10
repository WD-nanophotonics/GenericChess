# GenericChess F70 zero-compute policy-prior holdout audit

Work order: `GENERICCHESS-F70-ZERO-COMPUTE-POLICY-PRIOR-HOLDOUT-AUDIT`

Parent repository SHA: `7adb28c8da82cf88650695a7a77de0722d5d6fbf`.

## Scope and frozen inputs

This was a zero-compute falsification audit. It ran no search, training,
Arena, self-play, scorer fitting, seed sweep, new spectrum generation,
external engine, or Heavy job. It read only the persisted F62 96-root
spectrum units and the frozen Gen1/59011/59012/59013 checkpoint payloads.

The F62 stage identity is
`e7a93423d6058c68fe7ccbc61302584ca1e8869aa828586254f72f4dfdac2c70`.
The source splits are the frozen 48 fit, 24 development, and 24
final-holdout roots. Stable roots are those whose cached `root_40k` and
`root_80k` actions are equal; the deep-consensus action is the cached
`root_80k` action. Scorer tops use the existing offline total-Q rule
`base_q + frozen residual prediction`. The action-spectrum count is included
only when cached q10k and q20k select the same action.

## Split counts

| split | stable roots | Gen1 2k / deep | Gen1 static / deep | seed 59011 / deep | q10k=q20k / deep |
|---|---:|---:|---:|---:|---:|
| fit | 39 | 1/39 | 30/39 | 34/39 | 34/39 (defined 35) |
| development | 20 | 1/20 | 14/20 | 15/20 | 15/20 (defined 17) |
| final_holdout | 18 | 0/18 | 14/18 | 15/18 | 14/18 (defined 15) |
| development + final_holdout | 38 | 1/38 | 28/38 | 30/38 | 29/38 (defined 32) |

The aggregate stable set is 77 roots, matching F69. On stable shallow misses
only, q10k=q20k recovers the deep action 33/38 in fit, 14/19 in development,
and 14/18 in final holdout, for 61/75 overall, also matching F69.

## Decision

The untouched holdout comparison is positive for the existing 59011 scorer:

* combined development + final holdout: 30/38 versus Gen1 static 28/38;
* development: 15/20 versus 14/20;
* final holdout: 15/18 versus 14/18.

Therefore seed 59011 beats Gen1 static on the combined holdout and is not
worse on either untouched split. The cached q10k/q20k target also retains a
literal majority on both untouched splits: 15/20 on development and 14/18 on
final holdout (and 14/19 and 14/18 respectively among stable shallow misses).

Exact routing:

`EXISTING_59011_POLICY_PRIOR_HOLDOUT_SUPPORTED`

This F70 result records evidence only. It does not modify Native, AlphaBeta,
move ordering, checkpoint schemas, training, or Arena. A later work order may
perform the single causal root-hint probe described by F70.
