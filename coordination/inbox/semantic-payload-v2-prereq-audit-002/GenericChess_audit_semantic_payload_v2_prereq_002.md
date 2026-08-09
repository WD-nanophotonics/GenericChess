# GenericChess audit result: semantic payload v2 hardening

Audit target:
- base: `750c10a718cc045b8abdd0b992455131579be8d8`
- candidate: `38c554afb074aed391b23e356f36dc52e3d8a920`

## Verdict: PASS

The three previously blocking ABI findings are closed:

1. Duplicate v2 `type_ids` are rejected fail-closed.
2. Embedded NUL is rejected using a length-aware UTF-8 API, preventing C-string truncation and preserving exact identity semantics.
3. Explicit v1 compile + exact round-trip regression is present and confirms v1 capsules do not gain `type_ids`.

The implementation remains scoped to payload identity hardening and does not falsely enable semantic position/executor capabilities.

`38c554a` is accepted as the payload-v2 ABI prerequisite checkpoint for subsequent Native semantic position/hash/repetition/executor work.

Continue development in `sandbox`. A future executor checkpoint must receive its own SHA-bound audit.
