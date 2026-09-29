# Pawn-value sensitivity without material-prior validation

**Unknown.** On the frozen pawn capture/mate Chess root, is the no-quiescence capture choice actually sensitive to the pawn's control value, or only to action order?

**Smallest observation.** `scripts/audit_chess_pawn_value_ablation.py` holds the FEN, search implementation, depth 2, 2,000-node/five-second caps, disabled TT and ordering, and every other indexed F156 value fixed. It compares the original arbitrary pawn value `P=4` with one predeclared ablation `P=0`, under qsearch limits 0 and 4. This is a causal control, not a candidate prior or parameter search.

| Control pawn value | Qsearch limit | Selected action | Completed depth | Score |
| ---: | ---: | --- | ---: | ---: |
| 4 | 0 | Rb5xa5 | 2 | 12 |
| 0 | 0 | Kd1e1 | 2 | 12 |
| 4 | 4 | Kd1c1 | 2 | 999999997 |
| 0 | 4 | Kd1c1 | 2 | 999999997 |

The positive pawn value affects the shallow no-quiescence selection: capturing the pawn restores the material score, while with `P=0` the search selects a quiet move under the same control settings. Qsearch instead finds the same short forced mate in both arms. The earlier exact proof certifies both the original capture and Kd1c1 as wins; it does **not** certify the eventual outcome of the ablated Kd1e1 choice. Thus the ablation establishes material-value **decision sensitivity**, not material-value quality or a rule-derived coefficient. Selecting a value by this root would still require an independently justified loss objective and context-selection rule.
