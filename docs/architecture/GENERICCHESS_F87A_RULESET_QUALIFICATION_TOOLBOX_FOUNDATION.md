# F87A ruleset qualification toolbox foundation

F87A freezes a reusable qualification contract at baseline `a33ff404d33aef1d6717fc62e05337ae92691540`. It is a measurement foundation, not an automatic promotion claim. The negative and boundary controls remain calibration `FAIL`/`DEFER`; positive semantic controls now explicitly declare Layer B diagnostic-only and reduce playability status from blocking Layers A and C.

## Shared contract

`generic_chess.benchmark.qualification` is the single probe surface for:

- Layer A compiler/Core execution acceptance;
- Layer B displacement generators, integer lattice rank, lattice index/residue, finite-board reachability, SCC/component structure, sink fraction, reverse-edge fraction, opening-source coverage, same-type union coverage, component diversity, and materialized type profile;
- Layer C deterministic Common-Tape role-swapped trajectories with terminal/completion status, game length, branching, legal-action collapse, capture/check density, side-to-move bias, and opening identity sensitivity;
- Layer D/E report fields and explicit deferral semantics.

The F86M movement-lattice and F86N component helpers now delegate to this shared implementation. This keeps historical diagnostics compatible while avoiding a third script-only implementation.

## Status semantics

`PASS` means the bounded measurement or GenericChess-specific contract completed. `FAIL` is reserved for a violated hard gate. `DEFER` means a required admission layer is intentionally not measured or lacks a calibrated authority threshold. `UNMEASURED` identifies an inapplicable runtime probe. An ongoing game at `max_ply` is `CENSORED`, never a draw; unresolved classification remains `UNRESOLVED`.

Layer A is necessary but does not qualify a benchmark. Layer B is diagnostic: no universal rank-2/index-1 gate is applied. The F86N backbone is retained as an empirical diagnostic only. For positive semantic controls, the shared reducer records Layer B as diagnostic-only/non-blocking and uses Layers A and C as the blocking playability layers. `QualificationReport.hard_gates` exposes only integrity plus blocking qualification gates; diagnostic gates remain visible in `qualification_gates` without implying a block. The built-in Western Chess and Standard Shogi controls therefore do not fail because of a piece-local heuristic; their semantic-action runtime and dynamic terminal evidence provide the positive Layer-C scope evidence.

## Frozen calibration and budget

The PREP manifest covers the negative F86C legacy V4-3 and F86I full-reverse V4-3 controls, the F86N-R1 V4-3 and V5-3 boundary controls, and built-in Western Chess and Standard Shogi. It records source provenance, source hashes, and ruleset fingerprints.

The bounded calibration uses two paired role swaps per control, twelve plies, and a 32-entry PolicyTape. It uses zero search nodes, Arena games, training steps, and Heavy jobs. Paired Arena strength-response curves, Phase 1.7 shallow/deep diagnostics, and learning/evaluator adapters remain specified but deferred to a later approved stage.

The executable entry point is `scripts/f87a_ruleset_qualification.py`; it emits the ignored PREP and result evidence under `artifacts/f87a_ruleset_qualification/`. The durable behavior contract is covered by `tests/test_f87a_ruleset_qualification.py`, while this architecture note records the frozen schema, budgets, and interpretation rules.
