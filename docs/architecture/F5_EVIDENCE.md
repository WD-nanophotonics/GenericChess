# GenericChess F5 evidence

## 1. Status

`F5_RESULT = OPTIMIZATION_PASS`

The selected family was position-local semantic candidate/attack dispatch
reuse. It passed exact attack, legal-order, S3 reply-probe, search, full test,
and Native build gates.

## 2. Baseline and provenance

```text
starting sandbox = 363c74dc94217941f67edfbcfcd1bb84432f96a0
H5A              = 878e0e54afb69fe81eb8ccad1df9ddb56d8ac379
H5B              = 49022a5f80b5b9be6bd70cc2689f3ce4d250655c
audit followups  = cbf9e33, 74352db (harness-only)
origin/master    = 4f1d03a308f5fd04a01bbd980c7411888ea1ed9d
origin/chat      = d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

H5A is the harness-only state immediately before H5B. H5B contains the
production optimization and its candidate probe, but no after-outcome
evidence. Later audit-only commits corrected tracing and warm-up handling.

## 3. Certified corpus

The F4 legacy and continuous controls were reused together with four
reachable, nonterminal Semantic Standard Shogi prefixes. Every formal
semantic case uses the certified fingerprint
`5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345`.

The attack corpus queries all 81 squares for both owners (`162` queries per
prefix). Curated witnesses additionally cover anchor-safe/attacked states,
sliding and leaper attackers, blockers, captures, promotion, drops,
discovered attack/check relief, own-anchor exposure, and S4-bearing attack
contribution using deterministic generic S4 fixtures.

## 4. Baseline diagnosis

Before H5B, Profile A semantic cases performed approximately `1792–2043`
attack queries and `1355–1437` S3 trials. Profile B amplified this to
`8204–9871` attack queries and `4772–5899` S3 trials.

The F5 trace measured approximately `650k–672k` board-slot inspections for
the 162-query attack microbenchmarks. cProfile identified
`is_square_attacked`, `in_check`, `iter_legal_action_bindings`, and
`_trial_child_if_s3_legal` as the direct semantic costs. The repeated work
was full-board owner/current-type filtering inside pattern/type dispatch, not
TT, evaluator, or a change in search policy.

## 5. Optimization

H5B adds `_sources_by_owner_type()` in
`generic_chess/core/semantic_executor.py`. It builds a position-local,
board-order-preserving index keyed by `(owner, current_type_id)` and reuses
that dispatch within semantic attack and board-candidate generation.

The index is derived per operation, has no global mutable state, changes no
`Position`, fingerprint, serialization, public action, or history identity,
and leaves Core AI-unaware. Pattern, type, source, geometry, target, and
promotion order are preserved exactly.

Fixed-target geometry pruning, global attack caching, bitboards, incremental
attack maps, Native migration, TT changes, and Shogi-specific shortcuts were
rejected or deferred.

## 6. Parity

- Attack differential: all `162` square/owner queries per certified prefix,
  zero mismatches.
- Curated attack/S3 witnesses: zero attack mismatches; legal-action order and
  S3 reply-probe parity passed for all seven witnesses.
- Search parity: every before/after row matched action, score, PV, nodes,
  qnodes, completed depth, and termination reason.
- F3 history/TT, continuous-check, S4, interruptibility, Native-readiness,
  and Round 4 semantic regression suites passed.

## 7. Performance

Five measured repetitions followed one warm-up per case. Median semantic
aggregate wall time changed as follows:

```text
Profile A: 6016.505 ms -> 809.884 ms  = 86.5% improvement
Profile B: 37220.352 ms -> 4707.074 ms = 87.4% improvement
```

All four Profile A semantic cases improved by more than 85%; no semantic
Profile A case regressed. Profile B also improved substantially. Generic
controls remained within normal process noise and retained parity.

The post-H5B profile shows the remaining work in semantic legality/check,
runtime transitions, evaluator interaction, and the now-visible local index
construction. F5 authorizes no second optimization.

## 8. Validation and evidence

```text
focused F5/F4/semantic/S4/F3/search/history/interruptibility suites: PASS
full pytest: PASS at 100%
fresh supported Zig build: PASS, 333312 bytes
```

The machine-readable closure is under `artifacts/f5_semantic_attack_s3/`:

```text
baseline.json
corpus.json
attack_micro_baseline.json
s3_micro_baseline.json
profile_a_before.jsonl / profile_b_before.jsonl
profile_a_after.jsonl  / profile_b_after.jsonl
deep_profile_before_cumulative.txt / deep_profile_before_self.txt
deep_profile_after_cumulative.txt  / deep_profile_after_self.txt
hotspot_analysis.json
optimization_gate.json
attack_differential.json
legal_order_parity.json
search_parity.json
performance_comparison.json
final_verdict.json
manifest.json
```

`manifest.json` records SHA-256 values for the closure files and is verified
before delivery.

## 9. Final recommendation

F5 is closed. The only next phase recommendation is a separately gated
semantic target-directed legality/check investigation; do not begin it as
part of F5.
