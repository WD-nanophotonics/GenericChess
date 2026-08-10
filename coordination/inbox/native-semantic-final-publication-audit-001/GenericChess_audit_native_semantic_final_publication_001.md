# GenericChess Final Native Semantic Publication Audit 001

Target sandbox SHA:
`6ab4979ad7fc00a1afaa9aea42f508151b138d00`

Previous accepted publication base:
`9779d5d5dfbbadb38879f75ea396f60c7f78c784`

Active task:
`native-semantic-runtime-search-002`

## Verdict

**FAIL — small publication hardening required before final PASS**

The implementation is substantially complete and should be preserved. ADR-018, public semantic terminal/search, current-type board evaluation, exact-history terminal checks, PV replay tests, per-ruleset Native-executable derivation, and the major runtime/search differential work are all directionally correct.

Do not reset or discard the current implementation. Fix the findings below on top of `6ab4979`, rerun the focused/full gates, push a new SHA, and continue until final PASS.

## 1. BLOCKER — production fixed-depth search does not fail closed on non-exact history

The public terminal API correctly rejects a position whose non-empty history is only the legacy two-word projection. But `semantic_fixed_depth_search` is registered to the same `gc_semantic_probe_search` entrypoint, and that public search entrypoint does not perform the same exact-history precondition check.

Inside recursive search, `gc_semantic_terminal_status(...)` returns `< 0` for non-exact history, but `gc_semantic_probe_negamax` currently just returns the already-initialized result/material score. No exception is guaranteed.

Required:
- at the public production search boundary, reject `history_len > 0 && !history_exact`;
- preferably share a helper with `semantic_terminal`;
- propagate internal terminal/runtime failures rather than silently treating them as material leaves;
- add regressions for fixed-depth search and preferably probe search with legacy two-word history.

## 2. BLOCKER — global production capability flags are overclaimed

`6ab4979` changes:
`production_dynamic_evaluator = True`
`production_search_backend = True`

These are broader legacy/global capability names, not the semantic-specific gates authorized by the C1 supersede audit.

The current semantic evaluator is a generic board/hand material profile, not the project's broader dynamic evaluator, and the current fixed-depth semantic search is not yet the generic product SearchBackend integration.

Required:
- keep these broader flags false unless an independent existing contract explicitly says otherwise;
- if useful, add semantic-specific capability keys such as `semantic_terminal`, `semantic_fixed_depth_search`, `semantic_material_evaluator`;
- add tests distinguishing semantic runtime/search availability from broader product/backend integration.

## 3. BLOCKER — successor public ABI must not reuse frozen C1 Native version unchanged

ADR-017 froze Phase 1.9C-1 as Native `0.4.0` / schema `native-0.4.0` with a compile-only semantic public surface and semantic execution capabilities false.

ADR-018 now intentionally supersedes that public contract and adds semantic runtime, terminal, search, and changed capability semantics.

Required:
- create an explicit successor Native ABI/runtime version; preferred `0.5.0` / `native-0.5.0`;
- if an existing stronger versioning authority separates binary/public surface from schema, follow it but document an unambiguous successor runtime-contract version;
- semantic payload version may remain `2` if the payload layout itself did not change.

## 4. BLOCKER — preserve frozen C1 specification as historical evidence

`tests/specification/test_phase19c1_native_semantic_payload_contract.py` still identifies itself as the frozen C1 specification, but now asserts successor runtime capabilities as true.

ADR-018 correctly says it does not rewrite ADR-017 history. Tests should preserve the same property.

Required:
- move changed successor runtime/publication expectations into a clearly named ADR-018 / C2 successor specification file;
- keep the C1-named frozen specification focused on C1 static/payload invariants and historical meaning;
- do not make a file labeled frozen Phase 1.9C-1 assert the opposite of ADR-017.

## 5. ACCEPTED

Accepted and should be preserved:
- board evaluation by current type, hand by base type;
- ADR-018 supersede structure;
- fingerprint-bound semantic position;
- Unicode canonical key parity;
- exact full SHA-256 history;
- terminal-aware C recursion;
- C action buffer;
- trusted make/unmake;
- multi-seed/multi-fixture differential;
- perft;
- exact packed best action/PV and replay validation.

## 6. Final verification

After fixes, rerun:
1. Zig Native build
2. standard wheel/setuptools build smoke
3. semantic payload ABI suite
4. semantic position/runtime suite
5. randomized closure differential
6. successor ADR-018/C2 contract suite
7. final fixed-depth search/minimax/PV tests
8. legacy Native focused regressions
9. full pytest

Push a new clean sandbox SHA. Keep master unchanged. Do not return an intermediate progress report; continue until COMPLETE or genuinely HARD_BLOCKED.
