# GenericChess F68 deployment-aligned correction witness

Work order: `GENERICCHESS-F68-DEPLOYMENT-ALIGNED-CORRECTION-WITNESS`

Parent repository SHA: `0fb0702ad525f99b479fe6c4f7bcb70af9e9408d`.

This was a zero-compute alignment audit over the 96 persisted F62 roots. It ran
no new search, training, Arena, self-play, teacher search, external engine, or
Heavy job. Because no candidate had a safe analytic prefix, the conditional
2,000-node probe was not authorized and was not run. Detailed transient
arithmetic is in the ignored file
`.generic_chess_flow/f68-deployment-aligned-correction-witness/alignment.json`.

## Alignment audit

The audit compared each Gen1 static/evaluator top with the already cached Gen1
2k root action, then checked q10k, q20k, root40k, root80k, and the existing
stable/ordinary labels.

* Static top equals cached Gen1 2k action on only 8/96 roots.
* Among those aligned roots, 4 stable/ordinary roots have a q20k teacher top
  different from the deployed 2k action.
* Six aligned roots have at least two independent cached deeper signals
  converging on one alternative target.

This is the required precondition for a deployment probe: the prior root-44
correction failed because its static target was not the cached 2k action. F68
does not repeat that mismatch.

## Candidate safety results

For each aligned root with at least two deeper signals, the target was the
highest-supported alternative. The fixed-feature direction was then analyzed
with exact affine top-action intersections. A safe candidate needs the target
flip before the first unrelated unsupported change and before any high-
confidence change.

| root | target-support count | target | beta flip | first unrelated unsafe beta | safe? |
|---:|---:|---|---:|---:|:---:|
| 28 | 2 | `K [6,7]->[5,8]` | 1.813739 | 0.099902 | no |
| 55 | 2 | `P [3,4]->[3,5]` | 0.864764 | 0.135926 | no |
| 65 | 3 | `P [2,5]->[2,4]` | 0.748139 | 0.695505 | no |
| 83 | 2 | `B [4,4]->[3,5]` | 16.284384 | 1.194644 | no |
| 86 | 3 | `N [7,0]->[6,2]` | 1.656265 | 0.400437 | no |
| 87 | 3 | `N [1,0]->[0,2]` | 0.596508 | 0.226459 | no |

The strongest available support count is three, at roots 65, 86, and 87, but
each has an unrelated top-action transition before its intended target flip.
Root 65 is the closest of those by target support and static gap, yet its
first unsafe breakpoint `0.695505378231` still precedes its target flip
`0.748139371019`. Therefore no root satisfies the strict safe-prefix rule.

## Final classification

`DEPLOYMENT_ALIGNED_FIXED_FEATURE_CORRECTION_NOT_SAFE`

No child was materialized and no new 2k search was run. The result says that
the current fixed-feature one-direction correction cannot safely reach an
aligned deeper-supported deployment target on this cached corpus. Per the
work order, do not increase beta, add probes, run Arena, or start warm-start
training from this result.
