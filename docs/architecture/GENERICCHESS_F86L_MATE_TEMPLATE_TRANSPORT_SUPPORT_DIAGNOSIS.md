# F86L mate-template transport-support diagnosis

Status: diagnostic-only closed result after the zero-compute R1 routing
correction. Baseline:
`9be467cf954b3f8add59131ce86b933ee6f2cfa7`.

F86L did not create a ruleset candidate. It reran only the authorized V4-3
F86K census and analyzed the resulting fixed templates with compiled
empty-board mobility. No games, tactical probes, BFS game-state search,
teacher/search/training, F85 compute, or generator changes were performed.

## Census authority

The rerun reproduced the required values exactly: 156 candidate checks, 111
validated positions, 12 validated templates, complete (not truncated), with an
explicit diagnostic cap of 256. The compact evidence is in
`artifacts/f86l_mate_template_transport_support/diagnosis.json`.

The opening graph report includes all six ordinary pieces in the real V4-3
opening, their reachable-square sets, SCC/component IDs, file ranges,
owner-relative rank ranges, and `(file, owner-relative-rank)` footprints. The
template report preserves duplicate piece identity and computes exact
type-preserving maximum matchings, Hall deficiency, reachable/unreachable
source IDs, source-target displacement, and rank versus file/component failure
categories for all 12 templates.

## Result

No F86K template has a complete type-preserving opening-to-target matching:

| Template group | Maximum matching | Hall deficiency | Failure evidence |
| --- | ---: | ---: | --- |
| T0001, T0003 | 1 | 2 | rank |
| T0002, T0004 | 1 | 2 | rank plus file/component |
| T0005 | 0 | 3 | rank plus file/component |
| T0006 | 2 | 1 | rank |
| T0007, T0012 | 1 | 2 | file/component |
| T0008–T0011 | 1 | 2 | rank plus file/component |

The missing reverse counterparts relative to F86K are exactly:

- P0 ray `(1,0)` -> reverse `(-1,0)`, max steps 1;
- P1 ray `(1,1)` -> reverse `(-1,-1)`, max steps 2;
- P2 ray `(-1,1)` -> reverse `(1,-1)`, max steps 2.

Each singleton counterfactual was evaluated on the same 12 targets. Each
created additional SCC/component connectivity and opening-square reachability,
but each produced zero newly assignment-reachable templates. The exhaustive
seven nonempty support sets were also evaluated; none produced a complete
matching. Therefore there is no minimum support set that repairs this target
batch.

The F86I full-closure graph was evaluated on the same fixed F86K target batch
and also produced zero complete templates. F86I authority independently
records V4-3 full closure as 0/40 reachable, so the two results are consistent.
The corrected routing is
`REVERSE_CLOSURE_INSUFFICIENT_FOR_V4_3_KINEMATIC_MATE_TRANSPORT`, not an
evidence inconsistency. The result is target-specific transport/material
insufficiency, not a missing single reverse atom; the artifact retains the
exact source/target reachability needed for further review.

The executable routing recipe is now aligned with this authority: zero
full-closure reference templates routes directly to
`REVERSE_CLOSURE_INSUFFICIENT_FOR_V4_3_KINEMATIC_MATE_TRANSPORT`; a positive
full-closure reference distinguishes a smaller successful support,
full-closure-only support, and a positive-reference/no-success inconsistency.

## Compute and verification

Dynamic games: 0. Tactical nodes: 0. BFS expansions: 0.
Teacher/search/training: 0. F85 compute: 0. Default generator changed: false.

Exact verification command and result:

```text
.venv\Scripts\python.exe -m pytest tests/test_f86l_mate_template_transport_support.py
6 passed
```

R2 adds four direct routing-helper cases, for 6/6 total tests. This correction
added zero scientific compute: census 0, games 0, tactical 0, BFS 0,
teacher/search/training 0, F85 0.

F86L is closed with reverse closure ruled insufficient for the V4-3 transport
batch. No F86M candidate trial is authorized from this diagnosis; the next
diagnostic stage is the movement-lattice/component-invariant analysis.
