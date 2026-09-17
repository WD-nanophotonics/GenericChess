# F105 shallow exact learned ordering: cost gate failed

Work order: `GENERICCHESS_F105_CHESS_SHALLOW_EXACT_LEARNED_ORDERING_EQUAL_WALLCLOCK_ARENA2`

Baseline: `c1344c5a132f291216e12d50750bf156daf0ab00`

Scope: `A_CANONICAL_WESTERN_CHESS`, parent leaf/value checkpoint
`55249ef226ce60e51da8b6172881ea331757de0c72dbf918e48d84779dea1d5e`, and
the frozen nonlinear ordering checkpoint
`68136a6ea36fc9ab764bc7164e1fdb58c7cfbead718500dc9f51c0feedf0649f` with
model SHA256
`855537bd5f473c557e22eba7b2fccd51142d5572599e4075d93dd127c2942950`.

The Native path now accepts `ordering_max_ply` (`-1` preserves the historical
unbounded behavior; `1` applies the exact frozen learned legal-action sort only
at search-relative plies 0 and 1). The ordinary sort and tie-break are
unchanged. Search results and Arena progress metrics expose fixed-length
per-ply ordering and cache telemetry, and the bound is included in
`ArenaConfig`/resumable progress identity.

The fixed-node diagnostic used the prescribed 24 frozen F61R4 roots, 2,000
nodes, depth 12, TT8, and three fresh arms: A ordinary parent, B bound 1, and
C unbounded full ordering. B invoked learned ordering at both ply 0 and ply 1;
all B telemetry at ply >=2 was zero. C and A selected the same action on all
24 roots, so B had no C-vs-A differences to reproduce. Ordering elapsed was:

| arm | ordering elapsed |
|---|---:|
| B shallow bound 1 | 16.6631873 s |
| C unbounded full | 31.5419009 s |

The B/C ratio was `0.5282873518888014`, failing the required `<= 0.25`
cost gate. Per the work order, the run stopped before Arena2; no strength or
promotion classification was made. Final classification:
`SHALLOW_EXACT_ORDERING_COST_GATE_FAILED`.

Raw diagnostic evidence is retained outside Git at
`.generic_chess_flow/f105-chess-shallow-exact-learned-ordering-equal-wallclock-arena2/summary.json`.
