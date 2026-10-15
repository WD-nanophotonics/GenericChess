# Generic rule-win proof research prototype

This auxiliary implementation separates price-dependent play from a fixed,
price-independent rule-win prover. It lives on `sidemission`; it changes no
production search, defaults, UI, or primary checkout.

## Entry points

- `scripts.generic_win_proof.prove_win(compiled, state, target=None,
  max_nodes=4096, seconds=1.0, max_depth=64, cancel=None)` uses iterative AND/OR.
- `scripts.generic_win_proof_pn.prove_win_pn` accepts the same arguments and
  uses a best-first proof-number tree. It has no transposition merging.
- `verify_certificate` independently enumerates every defender action and
  checks the tree through the rules runtime. `StrategyCursor` verifies once,
  then `choose(state)` and `advance(state, actual_action)` follow that SAME
  tree after BOTH players' committed moves. Every move decreases its rank.
- `ProofMaterialPlayer` is an opt-in research adapter. Its normal arm can use
  the included material alpha-beta or an explicit mature-search callback.
  `proof_enabled=False` provides the normal-policy control. `proof_search`
  selects one frozen prover for all price candidates. An optional state-only
  `proof_trigger` can skip new proofs; it never discards an existing verified
  strategy. The default remains every ongoing state.

`PROVEN_WIN` includes an immutable root/history-bound `WinCertificate`.
`UNKNOWN` is not draw or loss. `ALREADY_TERMINAL` reports an actual rule
terminal and winner separately. Winning leaves can be checkmate, perpetual
check loss, or another supported rule win; terminal kind is preserved.

A `ProofNode` contains one legal target-player edge, every legal defender
edge, and actual winning leaves. Rank is a finite progress witness, not a
promise of shortest mate. `ProofResult.completed_depth` describes completed
AND/OR iterations; PN sets it to zero and exposes explored `peak_depth`
separately. Player decisions expose remaining `proof_rank` for future
conversion-versus-horizon audits.

## Semantics and limits

All legal quiet moves, captures, promotions, drops and pass actions come from
`SearchPathRuntime`. Full imported history stays authoritative; no board-only
proof cache or minimax tablebase labels are supplied to the prover. The exact
reference solver V3 remains unchanged and is not a deployment engine.

Declaration choices are absent from the runtime's board-action interface.
Rules containing them are explicitly refused. No-progress rules unsupported
by this runtime are also refused. Incomplete adjudication history gives
UNKNOWN; malformed input remains a caller error. Inconsistent imported
terminal metadata is rejected, rather than producing an unexecutable proof.
These exclusions restrict this prototype, not GenericChess's intended domain.

Cancellation and time limits are cooperative, including runtime legal/push
checkpoints. An indivisible import/terminal operation may finish after the
deadline; actual elapsed time is always recorded. Neither prover uses a
background worker. Nodes, memory and maximum proof depth are bounded.

## Resource accounting and actual games

The adapter reserves at most one quarter of the caller's visit allowance and
time for proof and one quarter for certificate verification. Ordinary search
receives the remainder; unknown proof never replaces it with a draw. A verified
continuation reuses its original strategy, with no new proof-node charge.
Public transitions and state/history checks still cost actual time.

Generic proof visits and mature-engine reported nodes are different work
units. Their allocation defines a reproducible policy, not equal primitive
cost. Mature `go nodes` can slightly overshoot: preserve reported counts and
`reported_node_overrun`; never clip them into the requested cap. Actual total
turn time, setup, verification and ordinary search remain observable.

The mature consumer in this study is the existing modified material-only
Fairy-Stockfish build, with aligned leaf/native/capture values, NNUE off,
Threads1 and fixed source/binary/config hashes. It is not unmodified Stockfish
or evidence about every mature engine. Ordinary concurrent machine work is
allowed; paired/counterbalanced assays do not imply exclusive timing.

Training maximizes actual win events minus loss events within the frozen
short horizon. Unfinished games remain UNKNOWN, contribute neither event,
and retain infinite-outcome bounds. They are never relabeled draws or given
piece-count rewards. This is an explicitly finite-horizon objective, not
infinite win probability. A complete proof longer than the remaining game
horizon may still be censored by that assay.

## Verification and reproducibility

Run the nine focused development modules: `test_generic_win_proof*`,
`test_generic_proof_player.py`, `test_generic_proof_interrupts.py`,
`test_generic_proof_tail.py`, `test_generic_proof_study_accounting.py` and
`test_generic_royal_actor.py`. They include public-transition promotion,
drop, pass-to-draw, played perpetual-check history, semantic pattern/auxiliary
identity, terminal priority, forged certificates, cancellation, shared budgets
and failed verification fallback.

Segment54 records frozen complete-library coverage, all-defense public replay,
paired algorithm comparison and actual short-game learning. Archived executed
sources retain earlier interface/diagnostic versions exactly; later metadata
repairs do not rewrite their outputs. Existing plans intentionally reject
mismatched live source hashes. Reproduce an old record with its archived
source version and pinned base/dependencies in a separate research directory,
not by overwriting an active checkout. New benchmark freezes use current code.
The prover itself has no tablebase dependency.

Proof-number search background: [Allis, van der Meulen and van den Herik,
1994](https://www.sciencedirect.com/science/article/pii/0004370294900043).
This implementation's correctness evidence is its finite-tree contract and
independent checks, not a claim that the paper validates this code.


## Physical completion after a short horizon

The opt-in `CertifiedTail` policy closes ordinary play at H16. If either player
already holds a verified, exact-history-bound strategy with remaining rank at
most64, play continues for at most that rank. The certified owner executes the
original cursor; defenders retain ordinary search. No new proof is attempted
after the horizon. Every committed public transition must reduce the stored
rank; only the actual rule terminal supplies a reward. Without an admitted
certificate the result stays UNKNOWN. Both colors and all prices use the same
admission rule. The original H16 snapshot, physical extra moves and costs stay
separate, and old H16 cohorts are never relabeled.

Thus B-to-D measures prices inside this fixed complete-player policy. A-to-B
includes both proof search and tail completion. It is not a comparison at equal
actual total cost or a claim about infinite-horizon WDL. Missing planned slots,
including unstarted games, remain in denominator bounds. An unfinished admitted
tail is an incomplete finite observation, not a zero completed event. Incomplete
TRAIN observations must not select a price.

`generic_proof_scaled_study.py` mechanically sizes the same closed KRN control.
The independent actor, public rule compiler and Native perft qualify actual
transitions. A different board also changes the state distribution and game;
it does not establish transfer to full Chess/Shogi or a universal price ratio.
The arbitrary fixed absolute price scale and mature engine's other search
constants remain part of the tested player. A best endpoint on a three-value
grid does not identify a continuous optimum. Shared coordinate paths reuse the
same actual grid games, not independent online learning trajectories.

## Optional paid-subtree research

`generic_win_proof_retained.py` is a separate experimental PN fork. It retains
at most16 already-proved depth-two future-own-turn subtrees by default, bound
to exact public state, history, target and rule fingerprint. Stored entries
remain candidate certificates until independently verified under the next
call's budget. No board-only merge, price input or automatic playback is added.
Collection, immutable-tree extraction and lookup are real costs; a cache-hit
microtime alone is not a net saving. The paid-path benchmark uses actual recorded
next moves, never chooses a future state because an entry exists, and excludes
already-proved parent strategies from incremental reuse claims. It is not the
default solver or a closed-loop player result.


For a public-valid rule that the mutable search runtime cannot import, such as
no-progress history, the adapter now obtains public legality and can still call
the supplied normal player under the remaining budget. Without such a player it
returns only an explicitly tagged public legal fallback; it does not claim an
internal material search or a proof. The prover's unsupported-history exclusion
remains. Atomic public generation is timed with cancellation/deadline checks
around it. This repairs the reproduced pre-normal-callback exception without
changing the supported runtime path used in the frozen KRN cohorts.
