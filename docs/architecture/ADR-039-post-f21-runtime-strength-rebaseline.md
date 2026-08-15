# ADR-039 — Post-F21 Runtime and Bounded Strength Re-Baseline

Status: Accepted as an audit decision; implementation deferred to a separately authorized phase.

## Context

F21 made the Native semantic legality provider the default production route while retaining Python authority for transition, history, TT, evaluator, ordering, qsearch, and search policy. Therefore the old F11/F14 hotspot list could no longer be treated as current evidence. F22 was authorized only to re-baseline runtime attribution and re-enter the preserved Round5 AlphaSho strength positions with bounded budgets.

## Evidence

H22A measured the four frozen semantic prefixes with Native legality on, Profile A/B, warm-up plus five formal runs. The provider remained active with zero fallbacks and zero operational failures. The evidence separates recorder inclusive/exclusive timing, cProfile cumulative/self views, Native payload/kernel/decode metrics, transition/runtime counters, evaluator, ordering, qsearch, and other search counters. No single new hotspot reached the strict two-profile 15% share and projected 8% end-to-end gain gate.

H22B used the exact ten preserved Round5 positions and read-only preserved AlphaSho moves. It did not run a game, rollout, tournament, 5000/20000 calibration, or long formal suite. Generic LOW/HIGH agreement was 2/10; maximum safe node agreement was 2/10. Eight disagreements persisted across the safe ladder and none were resolved by deeper search. Fixed-node Native ON/OFF parity was exact on 20 bounded rows after separating wall-clock safety from deterministic node controls.

The current generic-v1 evaluator derives piece values from movement capability, coverage/reachability/path metrics, drops, promotion relations, material, mobility, anchor escape, and check terms. Semantic legality is richer than this generic valuation vocabulary. For 280 authoritative child evaluations, the audit component sum exactly matched the production evaluator. All eight persistent AlphaSho reference moves ranked outside the current one-ply evaluator top-three.

## Decision

Select `RULE_DERIVED_EVALUATOR_V2` as the next boundary. The evidence meets the F22 persistence and evaluator-ranking gates and indicates a coherent generic feature-depth limitation rather than a single runtime winner or a purely search-depth-limited result. The future work must remain rule-derived and generic; F22 does not add hard-coded Standard Shogi values, change `EvaluationConfig`, or modify production behavior.

## Consequences

F22 closes with `AUDIT_PASS`, `POST_F21_RUNTIME_SINGLE_WINNER = false`, `PRODUCTION_BEHAVIOR_CHANGED = false`, and `F23_STARTED = false`. The next evaluator phase requires separate review and authorization. F4–F21 evidence and ADRs remain byte-identical, and all F22 artifacts are isolated under `artifacts/f22_post_f21_rebaseline_strength/`.
