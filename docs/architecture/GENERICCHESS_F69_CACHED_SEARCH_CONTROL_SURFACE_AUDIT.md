# GenericChess F69 cached search-control surface audit

Work order: `GENERICCHESS-F69-CACHED-SEARCH-CONTROL-SURFACE-AUDIT`

Parent repository SHA: `d5f91802f15e64292bd97ef1e8409f45c0cc8a24`.

This is a zero-compute audit of the persisted F62 96-root spectra and frozen
Gen1/59011/59012/59013 outputs. It ran no search, training, optimizer, self-
play, Arena, new spectrum, seed sweep, external engine, or Heavy job. The
machine-readable result is in the ignored runtime file
`.generic_chess_flow/f69-cached-search-control-surface-audit/audit.json`.

## Search-consistent reference

The stable reference set is the 77 roots where cached `root_40k` and
`root_80k` select the same action. On that set:

* 2 roots are `SHALLOW_CORRECT` (`root_2k` already equals the deep consensus);
* 75 roots are `SHALLOW_MISS`;
* all 75 misses retain the deep action in the cached action spectrum;
* q20k recovers the deep action on 61/75 misses;
* q10k equals q20k and that common action equals the deep action on 61/75
  misses.

Thus the action-spectrum target is search-consistent on a clear majority of
candidate-covered shallow misses; there is no retained-spectrum coverage
failure in this stable-miss set.

## Existing scorer thought experiment

Each scorer is evaluated only as an offline root move-ordering/policy prior;
none is deployed as a leaf evaluator and no search code is changed.

| scorer | shallow-miss recovery | correct retention |
|---|---:|---:|
| Gen1 static | 57/75 | 1/2 |
| seed 59011 | 62/75 | 2/2 |
| seed 59012 | 61/75 | 2/2 |
| seed 59013 | 61/75 | 2/2 |

All three replacement scorers satisfy the literal dominance rule, but the
deterministic tie-break selects exactly one: seed 59011, with five additional
miss recoveries over Gen1 and no retention loss. For example, on root 0 the
cached 2k action is `B [0,6]->[2,8]`, while the deep consensus and all four
cached scorer tops select `K [5,8]->[6,7]`; on root 1 the deep action is
`P [6,2]->[6,3]` and q10k agrees while q20k selects another action, showing
why q10k/q20k agreement remains a diagnostic condition rather than an
assumption.

## Final route

`EXISTING_REPLACEMENT_REUSABLE_AS_POLICY_PRIOR`

Selected scorer: **seed 59011**.

This result only authorizes considering seed 59011 as a direct search-control
or move-ordering prior in a later work order. It does not authorize modifying
AlphaBeta, Native move ordering, creating a policy-head schema, materializing
another checkpoint, training, or running Arena in F69.
