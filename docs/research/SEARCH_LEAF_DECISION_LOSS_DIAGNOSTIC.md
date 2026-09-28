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

**Next bounded observation.** Inspect the actual evaluator call sites and search budgets for Western Chess and Standard Shogi. Determine whether one fixed horizon and leaf-state ensemble really describes deployment. If not, predeclare a small bounded-search validation contract and report any depth dependence instead of calling its selected coefficients rule-implied static values. Leave Xiangqi material values sealed until a formula is frozen.
