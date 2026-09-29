# Bounded-search decision-loss diagnostic

**Unknown.** Does the cheap material prior's use as a search-leaf evaluator supply a game-independent type ranking once the objective is exact root decision loss?

**Smallest observation.** Evaluate one finite, deterministic, zero-sum game at two fixed cutoff depths. The maximizer at the root chooses `left` or `right`; all later moves are forced. At the third ply, `left` terminates in Loss (`-1`) and `right` in Win (`+1`). Thus exact minimax selects `right`, and choosing `left` incurs decision regret `2` under this *declared* payoff coding. No probability, self-play, human value, or holdout enters the example.

At a nonterminal cutoff, suppose the candidate static material evaluator is `E(s)=w_A n_A(s)+w_B n_B(s)`. The graph has legal forced transitions whose leaf inventories are:

| Root action | Depth 1 leaf `(n_A,n_B)` | Depth 2 leaf `(n_A,n_B)` | Exact terminal outcome at depth 3 |
| --- | --- | --- | --- |
| `left` | `(1,0)` | `(0,1)` | Loss |
| `right` | `(0,1)` | `(1,0)` | Win |

This is a synthetic game graph: its material inventories are state labels, and the forced transitions exchange which type is present. It is not claimed to be a Chess, Shogi, or Xiangqi fixture. At each cutoff choose the branch with larger `E`; a tie selects `left`, fixed before the comparison. Direct enumeration gives:

| Weights | Depth 1 choice/regret | Depth 2 choice/regret |
| --- | --- | --- |
| `w_A>w_B` | `left / 2` | `right / 0` |
| `w_B>w_A` | `right / 0` | `left / 2` |
| `w_A=w_B` | `left / 2` | `left / 2` |

The table was checked by evaluating the two leaf scores for all three order classes. A single context (the root), fixed terminal outcomes, and exact root decision loss do **not** identify a ranking that succeeds at both horizons. At either *preselected* horizon the zero-regret ranking is clear, but its numerical magnitude remains unidentified. The result concerns horizon dependence, not a proof that a useful static approximation at a declared deployment horizon is impossible. The tie policy is explicit because leaving it unspecified would let equal weights conceal the ranking conflict.

**Scientific boundary.** Decision regret is a defensible use objective for an evaluator, but the search horizon and cutoff state semantics are additional model choices. They may be fixed by a deployment budget rather than by RuleSet semantics. Changing the horizon may change what the same scalar must rank. No type coefficients should be tuned to make this finite witness agree with a human table.

## Quiescence extension on the same exact graph

The 2026-09-29 sourced Chat consultation
(`GENERICCHESS-20260928-232122-5dee9cfc`) suggested separating nominal cutoff depth
from the actual evaluation frontier. Reuse the frozen graph and exact terminal
labels above; add a declared quiescence rule that extends **only** the forced
second-ply transition after each depth-1 leaf, then evaluates at its depth-2
successor. No terminal label, inventory, or material coefficient changes.
The opponent has one legal continuation on each branch, so minimax backup
adds no separate choice at this ply.

| Operator | Left evaluated inventory | Right evaluated inventory | Zero-regret ranking |
| --- | --- | --- | --- |
| Depth 1, no extension | `(1,0)` | `(0,1)` | `w_B>w_A` |
| Depth 1, forced-transition extension | `(0,1)` | `(1,0)` | `w_A>w_B` |
| Depth 2, no extension | `(0,1)` | `(1,0)` | `w_A>w_B` |

This follows by direct substitution in `E=w_A n_A+w_B n_B` and the existing
exact choice `right`; equal weights choose the losing `left` under the frozen
tie rule. The extension makes the *actual frontier* identical to depth 2 and
therefore reverses the depth-1 ranking requirement. This is an analytic
control, not evidence that any Chess or Shogi quiescence policy finds a
universally correct frontier. It strengthens the deployment boundary:
nominal depth alone does not specify a material-prior decision objective.
It supplies no context weighting, type utility, or scalar unit.
Direct arithmetic with three order classes (`w_A>w_B`, `w_B>w_A`, tie)
reproduced the choices: `left/right/left` at depth 1 without extension and
`right/left/left` at either deeper frontier.

**Subsequent observations.** `SEARCH_DEPLOYMENT_CONTRACT_AUDIT.md` inspected the actual search call sites and budgets. `CHESS_QSEARCH_BOUNDARY_PROBE.md` and the later labelled mate controls tested concrete Chess roots; none derived a relative material unit. A future search-use validation must predeclare its operator, resource budget, contexts, and regret aggregation rather than call a selected coefficient rule-implied. Leave Xiangqi material values sealed until a formula is frozen.
