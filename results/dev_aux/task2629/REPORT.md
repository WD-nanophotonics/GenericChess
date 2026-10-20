# Task2629 fresh-root H=256 evaluation

## Result

Task2629 reused the four audited task2628 initial/TDLeaf weight pairs without
training or modification. It evaluated 16 new outcome-blind rules15 roots on
the frozen 4-seed x 2-color x 2-endpoint panel. All 256 registered slots
completed in 228.46 seconds, using 8,850 queries and 154,053 nodes, below the
1,800-second evaluation cap. The independent full-history, legal-action,
actor, terminal/reward, UNKNOWN and per-root node-cap audit passed.

There were 251 actual terminal slots and five UNKNOWN endpoints. The UNKNOWNs
were all HORIZON_UNKNOWN; none reached its per-root node cap. W/L/D by endpoint:

| Endpoint | Wins | Draws | Losses | UNKNOWN |
| --- | ---: | ---: | ---: | ---: |
| Initial weights | 59 | 7 | 59 | 3 |
| TDLeaf weights | 60 | 4 | 62 | 2 |

Of 128 paired strata, 123 had both outcomes known and five had one UNKNOWN
endpoint each. With every UNKNOWN independently ranging over `[-1,+1]`,
TDLeaf-minus-initial has finite completion sum bounds `[-7,3]` and mean bounds
`[-7/128, 3/128]` (`[-0.0546875, 0.0234375]`). These bounds are not confidence
intervals. They include both signs and do not establish that TDLeaf improved
or harmed strength. UNKNOWN remains censored, never a draw.

## Freshness, censoring and scope

The 16 roots came from family range `[300000,350000)`. The independent source
audit checked the pinned 55,385-history inventory, all 136 task2627 train/eval
roots and all task2628 train/eval query/episode histories; exact-record
intersections were zero. It replayed every selected full history and verified
a legal hand-R unlock action at all 16 roots. Preparation and audit took
39.341 and 37.655 seconds. These checks establish exact-record separation only,
not descendant, transposition, distributional or population independence.

This is a separately registered evaluation-only panel, not an extension of
task2628. Task2628's 17/256 H=128 UNKNOWN slots were all horizon-limited with
17,486–38,041 unused nodes per slot. A post-hoc diagnostic found some position
with three repetitions in each such history; the final position count was one
in 11 histories, two in five and three in one. Rules15 declares a repetition
limit of four and defaults to repetition draws. Task2629 doubled H while
retaining the same per-root 20k/40k node caps. Its five remaining UNKNOWNs also
stopped at the horizon and retained at least 16,717 nodes of headroom. The
different panels cannot isolate a causal effect of H, and these studies are
not pooled after seeing their outcomes.

The task2629 plan SHA-256 is
`f05e148bef90c76ed7246a7fcc283a565b4aafb1eaf8d09444d5e634eadc4fb1`; the
evaluation result SHA-256 is
`591975055c16046adaefc2be900297e39ad432ec5d719aaeb108e9858ae3eddf`.
The conservative all-in bound was 3,540 seconds (59 minutes), including
preparation, both audits and reserve; it was below the 120-minute assessment
threshold and the existing project cap. No training, prior cap change, sample
top-up or result pooling occurred.

## Verification and next step

- Root preparation/audit: 16/16 replayed, zero exact-history overlaps,
  16/16 legal unlock actions.
- Evaluation: 256/256 slots; exit code 0; launcher receipt and log hashes
  recorded under `run/`.
- `audit_evaluation.py`: PASS, 8,850 queries, 154,053 nodes, 251 actual
  terminals, five UNKNOWN.
- `analyze_corrected.py`: PASS; plan, registration, result, audit and root
  hashes are bound. The pinned analyzer remains unchanged.
- `test_design.py`: three tests passed; all task2629 Python sources compile.

Task2628 and task2629 are two separate finite panels on one generated 4x4
semantic-action ruleset. Neither establishes broad Generic transfer. The next
learner step should test a separately registered rule/mechanic with the same
fixed-scale TDLeaf route, rather than reuse these exposed roots or keep
expanding rules15 evaluation.
