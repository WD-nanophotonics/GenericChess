# F86M V4-3 movement lattice and component-invariant diagnosis

Status: completed final static diagnosis. Baseline:
`26005ae40f834a7180e8ad7a6b0dee8e2f478ce3`.

F86M creates no ruleset candidate and changes no generator behavior. It uses
the F86K 12-template batch and F86I full-closure 40-template batch as fixed
authority, with execution-time caps of 256 and 512 candidate checks
respectively, total cap 768. The run reproduced F86K 156/111/12 and F86I
504/398/40 exactly, for 660 total checks; both censuses were complete.

## Lattice and component result

The analysis uses owner-0 displacement generators, treating a RAY as its
primitive direction and a LEAP as its exact displacement.

| Type | Generators under full closure | Lattice rank | Index | Invariant |
| --- | --- | ---: | ---: | --- |
| P0 | `(1,0)`, `(-1,0)` | 1 | — | rank coordinate is invariant |
| P1 | `(-1,1)`, `(1,1)` and reverses | 2 | 2 | `file + rank mod 2` |
| P2 | `(1,2)`, `(-1,1)` and reverses | 2 | 3 | `file + rank mod 3` |

Finite-board full-closure components are:

- P0: 4 components of size 4; its two opening owner-0 pieces start in distinct components.
- P1: 2 components of size 8; its opening owner-0 piece is in component 0.
- P2: 3 components of sizes 6, 5, and 5; there is no opening owner-0 P2 piece in this material.

Opening-source coverage is correspondingly limited: P0 reaches 8/16 squares
from its two sources with component diversity 2; P1 reaches 8/16 from its one
source; P2 has zero opening sources and zero union coverage. Pairwise P0 source
overlap is zero. The complete per-source graph footprints and component IDs
are retained in the diagnosis artifact.

## Template matching decomposition

Every target edge records source and target identity, displacement, lattice
invariant values, lattice membership, finite-board component IDs, and actual
empty-board graph reachability. Matching is staged as lattice-admissible,
finite-component, and final type-preserving bipartite matching, with Hall
deficiency retained per template.

| Batch | Templates | Lattice-blocked | Component-only blocked | Hall-only blocked | Complete assignment |
| --- | ---: | ---: | ---: | ---: | ---: |
| F86K | 12 | 12 | 0 | 0 | 0 |
| F86I | 40 | 40 | 0 | 0 | 0 |

The primary route is therefore:

`MOVEMENT_LATTICE_INVARIANTS_DOMINATE_V4_3_TRANSPORT_FAILURE`

This explains why reverse completion, backward-rank capability, and full
reverse closure are insufficient: the target transport is blocked before
finite-board connectivity or duplicate-piece Hall capacity can rescue it.
The result does not impose an index-1 requirement on future pieces; it records
movement-lattice rank/index as a generator-quality diagnostic alongside
opening material placement and target-specific matching capacity.

## Compute and verification

New real games: 0. Tactical nodes: 0. BFS expansions: 0.
Teacher/search/training: 0. F85 compute: 0. Default generator changed: false.

Exact verification command and result:

```text
.venv\Scripts\python.exe -m pytest tests/test_f86m_v4_3_movement_lattice_invariants.py
4 passed
```

The durable compact evidence is in
`artifacts/f86m_v4_3_movement_lattice_invariants/diagnosis.json`. Raw transient
benchmark output is not tracked.
