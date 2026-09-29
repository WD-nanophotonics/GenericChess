# Immediate-mate root cannot expose quiescence choice

**Unknown.** Can the independently certified Chess root in `CHESS_ROOT_TERMINAL_LABELS.md` compare quiescence-off and quiescence-on root decisions against its exact immediate outcomes?

**Smallest observation.** Run `scripts/audit_chess_qsearch_boundary.py --fen "8/8/8/1R6/8/8/5R2/k1K5 w - - 0 1"` with the prior frozen indexed material control. It attempts nominal depths 1 and 2, quiescence limits 0 and 4 (hard cap 8), with no TT or ordering and at most 2,000 total nodes and five seconds per run. The script now reports the selected child's terminal status as well as the search result.

| Nominal depth | Quiescence limit | Selected action | Child label | Completed depth | Q nodes | Termination |
| --- | --- | --- | --- | ---: | ---: | --- |
| 1 | 0 | Rb5a5 | White checkmate win | 0 | 0 | `root_immediate_win` |
| 1 | 4 | Rb5a5 | White checkmate win | 0 | 0 | `root_immediate_win` |
| 2 | 0 | Rb5a5 | White checkmate win | 0 | 0 | `root_immediate_win` |
| 2 | 4 | Rb5a5 | White checkmate win | 0 | 0 | `root_immediate_win` |

Each run used 17 main nodes and returned score 999999999. The searcher's root immediate-win check selects a certified mate before nominal depth 1 or quiescence is reached. The exact label validates the selected outcome, but this fixture supplies **no quiescence comparison**. Increasing depth or repeating this root would not answer the quiescence question.

**Decision.** The next Chess validation root must avoid an immediate winning action that triggers this shortcut, yet have independently established distinct root-action outcomes. Seek a bounded forced-outcome certificate or a reliable endgame tablebase comparison before interpreting quiescence-related decision loss. Keep the arbitrary indexed profile separate from any proposed material prior.
