# Frozen Chess quiescence boundary probe

**Unknown.** On the F156 Western Chess root, does changing only the Python search quiescence limit change a completed fixed-depth root result under the same indexed material control?

**Smallest observation.** Run `scripts/audit_chess_qsearch_boundary.py` on F156 `w1` (`4k3/8/8/p7/8/8/8/R3K3 w - - 0 1`) at nominal depths 1 and 2, with quiescence depth 0 or 4 (hard cap 8), no transposition table or ordering, at most 2,000 total nodes and five seconds per run. The piece-index material profile is inherited unchanged from F156. This is a search-boundary control, not a proposed prior.

| Nominal depth | Quiescence depth | Selected action | Score | Main nodes | Q nodes | Completed depth |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | 0 | Ra1xa5 | 6 | 25 | 0 | 1 |
| 1 | 4 | Ra1xa5 | 6 | 25 | 12 | 1 |
| 2 | 0 | Ra1xa5 | 6 | 59 | 0 | 2 |
| 2 | 4 | Ke1f1 | 6 | 55 | 138 | 2 |

All four runs completed their requested depth under the bounds. Thus the quiescence setting changes the selected action at depth 2 on a real Chess RuleSet root, while the reported best score remains tied. The action difference alone does not establish distinct minimax quality: the probe supplies no independent exact root-action outcomes, and the indexed values are arbitrary. The same score also prevents attributing a score improvement to quiescence here. F156's native no-quiescence comparison remains an existing control; this probe does not repeat it. Standard Shogi and Xiangqi were not used to select a formula.

**Decision.** Treat the search boundary as an explicit validation parameter. Next seek a frozen Chess root with an independent exact action-outcome label before measuring decision loss. A bounded mate or tablebase certificate would qualify only if it covers the compared actions under the full relevant rules; do not infer quality from the searcher's own score or from this tie.
