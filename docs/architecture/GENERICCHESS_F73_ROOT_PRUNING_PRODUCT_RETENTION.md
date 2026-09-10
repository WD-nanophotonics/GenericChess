# F73 Root-Pruning Product Retention

Date: 2026-09-11  
Work order: `GENERICCHESS-F73-ROOT-PRUNING-PRODUCT-RETENTION`  
Baseline: `0732a9b78d7c58d7554441271133c4be8f427b8d`

## Retention decision

F72’s opt-in root-window-pruning control passed the F73 retention matrix and
is retained as the normal `SemanticSearchEngine` product default. The low-level
Native semantic API remains backward-compatible with `root_window_pruning=False`
by default. Historical F59/F62/F71 audit paths explicitly pin
`root_window_pruning=False` so their frozen full-window evidence remains exact.

No learned root hint is loaded. No final holdout, training, Arena, self-play,
external-engine comparison, or Heavy job was run.

## Exactness gates

TT-off depth-1/2 exactness covered the 20 F62 stable development roots, Western
and Standard Shogi initial product positions, the existing declaration claim
fixture, and existing continuous-check, repetition, and automatic max-ply
semantic fixtures. The 52 comparison rows had exact action, score, declaration/
terminal result, selected PV, root-state preservation, and repeatability.

The fixed depth-3 subset covered 8 existing F62 roots and passed exact parity.

The persistent-TT gate covered 9 representative Western/Shogi/declaration
positions at depths 1/2 (18 rows). Cold full-window versus pruning and repeated
same-engine warm-TT pruning all passed action, score, declaration, selected-PV,
and determinism checks.

## Efficiency matrix

The 20 F62 development roots used fresh 8 MiB TT engines for fixed depth 2 and
fresh 8 MiB TT engines at a 2,048-node iterative budget.

| Measure | Full window | Root pruning | Delta |
| --- | ---: | ---: | ---: |
| fixed-depth nodes, total | 19,879 | 7,227 | -12,652 |
| fixed-depth beta cutoffs, total | 0 | 462 | +462 |
| 2,048-node completed-depth sum | 39 | 40 | +1 |

Fixed-depth node regression over 10%: none. The largest per-position change was
an improvement (root 83: 922 to 574 nodes, -37.74%). At the capped budget,
full-window completed depths were `1:1, 2:19`; root pruning completed `2:20`.
TT cutoffs were zero in both fixed-depth aggregates; per-position TT
probe/hit/cutoff telemetry is retained in the ignored raw result.

Classification: **ROOT_PRUNING_PRODUCT_SUPPORTED**.

The product integration is limited to the default search strategy switch and
historical audit pins. Targeted integration plus affected semantic suites pass;
the next Courier order controls any further work.

The ignored raw pre-integration matrix is
`.generic_chess_flow/f73-root-pruning-product-retention/f73_results.json`,
SHA-256
`b5f16321b2d1b8e7b04c9eabb2f8c51ccce85f930a0ab96acdfd16e965b1e403`.
