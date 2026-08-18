# GenericChess audit: semantic payload ABI prerequisites

Audit target:
- base master: `3629c52b8c0bb4e92bd55851f2fc970d0407dadc`
- `a5fd94eb9940330904e73c2714335e02edd504a7`
- `750c10a718cc045b8abdd0b992455131579be8d8`

## Verdict

### a5fd94e — PASS

Both changes are correct and necessary:
1. `native_semantic_rules.c` is added to the setuptools extension source closure.
2. `GCSemInvariant.refs_count` is widened from `uint8_t` to `uint16_t`, matching `sem_parse_square_refs(..., uint16_t *count, ...)` and eliminating the previous adjacent-memory overwrite hazard.

No blocking issue found in this commit.

### 750c10a — FAIL (small hardening required before treating payload-v2 ABI as frozen)

The overall design is accepted:
- payload v2 adds C-owned stable `type_ids`;
- v1 remains accepted as compile-only;
- v2 requires `type_ids`;
- `semantic_position_state` / `semantic_s0_s4_executor` correctly remain false;
- `native-0.4.0` does not need to be bumped solely because the semantic payload has its own explicit ABI version.

However, fix the following before considering the v2 identity ABI closed.

## Finding 1 — duplicate v2 type IDs are accepted

High-level RuleSet validation guarantees unique type IDs, but the C public payload parser is independently fail-closed and accepts arbitrary payload dictionaries.

For payload v2, after reading `type_ids`, reject duplicates.

Reason: v2 exists specifically to make public type identity part of the C-owned semantic runtime. Duplicate identities make the index→public-ID mapping non-injective and would poison semantic position identity / repetition / hashing assumptions.

Add a regression that mutates a valid v2 payload to contain duplicate `type_ids` and verifies compile failure.

## Finding 2 — embedded NUL silently breaks exact identity

Current code obtains `const char *text = PyUnicode_AsUTF8(item)` and then uses `strlen(text)` / later `PyUnicode_FromString(...)`.

A Python `str` may contain U+0000, and current RuleSet validation only requires a non-empty unique string; it does not forbid embedded NUL.

Therefore a legal high-level type ID such as `"A\0B"` can be lowered, but C storage truncates it to `"A"`, violating exact payload round-trip and stable identity.

Choose one explicit contract and test it:
- preferred minimal ABI fix: fail closed in v2 parser when the UTF-8 representation contains embedded NUL, using a length-aware Python API (`PyUnicode_AsUTF8AndSize`) and rejecting any NUL inside the returned byte span; or
- deliberately narrow the high-level RuleSet type-ID contract to forbid U+0000, with validation/spec/regression changes.

Do not silently truncate.

## Finding 3 — add an explicit v1 compatibility regression

The implementation appears structurally capable of v1 compatibility: it accepts payload versions 1/2 and only emits `type_ids` in reconstructed payload for v2. But the changed test files do not contain an explicit v1 round-trip regression.

Add a deterministic test:
1. start from a valid v2 payload;
2. remove `type_ids`, set `semantic_payload_version = 1`;
3. compile it through the C API;
4. assert `semantic_rules_info()` exactly equals that v1 payload;
5. assert v1 does not accidentally gain a `type_ids` field.

This makes the stated compatibility guarantee executable rather than incidental.

## Non-blocking notes

- Partial-allocation cleanup of `char **type_ids` looks sound because the rules object is calloc-zeroed and `free(NULL)` is safe.
- The Python lowering order (`tuple(sorted(support.type_metadata))`) aligns `type_ids` and `types` deterministically.
- Keeping executor capability flags false is correct.
- Continue semantic-position/executor development in parallel if useful, but land these v2 ABI hardenings before depending on v2 type identity in hash/repetition/position-key code.

After fixes, push the new sandbox SHA. The old audit is SHA-bound and does not automatically PASS the replacement commit.
