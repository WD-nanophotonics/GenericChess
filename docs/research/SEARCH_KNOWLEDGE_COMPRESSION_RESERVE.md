# Low-parameter search knowledge — medium-term reserve

Status: NOT current Main; no training, TT replacement, defaults or new workers.
Current P0/P1 structural truth and rule counterfactuals remain first, followed
by matched explorer calibration, conditional learning/strong teachers, then
inverse design. Source: [Chat1792815705](https://nanomelon.slack.com/archives/C0C6L21UU20/p1792815705985309).

A minimal rule-conditioned model could output a piece-order class, move order,
cutoff/refutation priority or a small resource-allocation decision. Its target
is correct decisions/proofs at lower total cost, or higher correct decision
quality at equal wall time. Include feature extraction, inference, training
and engineering cost. A PV first move is not automatically the cheapest cutoff
label. Linear/integer rules are legitimate competitors to small networks.

First isolate ordering while preserving the full search-tree/terminal/history
semantics and all other pruning settings. Compare existing TT/capture/killer/
countermove/history/staged-picker controls; calibrate on old exact toys, then
freeze genuinely new rule-level tests. Only later consider learned extensions,
LMR/pruning, qsearch or Goal Solver calls, whose correctness may change.

Claude1792817437 notes that history-aware TT keys may reduce reuse. This is
a code-based hypothesis, not measured TT hit rate or speed evidence. Treat
implementation throughput and learned algorithmic benefit separately. A
position-key move hint, checked against actual legal moves, can preserve
ordering-only semantics. Reusing position-key exact/lower/upper bounds while
merely testing repetition at the current node can change results: the new
H6 both-ongoing LOSS/DRAW witness has equal Position and remaining clock but
different future repetition stops. Such a cache is an approximate semantic
intervention, not an equivalent cheap baseline or an order-only ablation.
Measure any future approximation's errors separately; do not weaken history
correctness to inflate learned-ordering gains. No cache implementation here.

The earlier feature policy failed because RuntimeSearchState lacked public
repetition_counts. A later private runtime-property read bridge passed parity
checks only; it was not a repaired policy execution. Projection cost remains
unmeasured. Future callers should first identify a supported incremental API
and measure actual use, rather than equating runtime capability with speedup.

Retain the original October16 long-term records:
[small-board teachers](https://nanomelon.slack.com/archives/C0C6L21UU20/p1792117966727689),
[NNUE transfer](https://nanomelon.slack.com/archives/C0C6L21UU20/p1792118043431309),
[pure-Leaper parameter transfer, not launched](https://nanomelon.slack.com/archives/C0C6L21UU20/p1792156154268769).
The reported YaneuraOu results in Chat's memo are third-party experiment
evidence under specific opponents/hardware; they neither isolate evaluation
nor establish an applicable GenericChess gain.

Current structural qualification: [history context](LEAPER_HISTORY_CONTEXT_20261024.md)
proves a scoped game-suffix key, not an arbitrary finite-heuristic key. Two
actual Core histories with the same complete50node suffix can have different
hypothetical D1scores if a feature reads forgotten history. Any future cache
consumer must establish evaluator/feature and controller factorization before
sharing bounds. The present20newsemantic/77compatibilitychecks and semantic
state reductions are not measured engine/learner acceleration.
