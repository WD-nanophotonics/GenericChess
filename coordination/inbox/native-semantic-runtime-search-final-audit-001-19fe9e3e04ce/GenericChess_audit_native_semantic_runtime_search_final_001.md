# GenericChess Final Audit — Native Semantic Runtime/Search

Candidate SHA: `1303c03b114434cc6dc05bc94abe23cec8940437`
Base master SHA: `3629c52b8c0bb4e92bd55851f2fc970d0407dadc`

## Verdict: PASS

The exact sandbox candidate is accepted for the scope of `native-semantic-runtime-search-002`.

Verified in the candidate:

- ADR-018 explicitly supersedes the ADR-017 C1 compile-only boundary without rewriting C1 history.
- Native ABI/runtime is explicitly versioned `0.5.0` / `native-0.5.0`; semantic payload remains v2.
- `semantic_position_state` and `semantic_s0_s4_executor` are published separately from broader production-backend claims.
- `production_dynamic_evaluator` and `production_search_backend` remain false.
- Semantic-specific terminal / fixed-depth search / material-evaluator capability keys are explicit.
- public terminal/search reject non-empty non-exact repetition history.
- recursive search propagates terminal-authority failure instead of silently treating it as a material leaf.
- board material uses current type; hand material uses base type.
- C1 static specification evidence is preserved; successor runtime/version/capability assertions live in the C2/ADR-018 specification.
- sandbox remote points exactly to this candidate; master remains at the stated base SHA.

The Agent reports Zig build, wheel smoke, C1/C2 suites, semantic runtime/search suites, legacy Native regressions, and full pytest all green. Those final-test results satisfy the Agent-side test gate for this candidate.

## Promotion invariant

This PASS is SHA-bound to `1303c03b114434cc6dc05bc94abe23cec8940437`.

Any post-audit modification or new commit invalidates the PASS and requires a new audit.
Do not modify the candidate merely to record this audit.

For later promotion to master:
- use this exact candidate SHA;
- verify final tests on this exact SHA;
- verify clean worktree;
- exclude coordination artifacts / unrelated junk from the promoted product tree;
- no force push.
