# F1 identity call-site migration matrix

This matrix records the direct identity consumers audited before the F1
implementation.  The compatibility helpers remain present for fixtures and
parity tests, but migrated production code has one authority.

| Area | Before F1 | F1 owner / disposition |
|---|---|---|
| `core/transition.py` | Chose semantic or legacy key in each branch | `repetition_identity_key` |
| `core/lazy_transitions.py` | Repeated the same branch while caching child keys | `repetition_identity_key`; lazy override is Core-issued |
| `session/session.py` | Always recorded legacy `position_key` | `position_identity_key` for before/after records |
| `ui/controller.py` | Root/stale checks used legacy key | `position_identity_key`, so aux-only changes invalidate results |
| `ui/dialogs/diagnostics_dialog.py` | Displayed legacy key | `position_identity_key` |
| `ai/alphabeta/search.py` | Local semantic-vs-legacy selection and tuple assembly | `search_state_identity`; keeps repetition, ply, and adjudication context |
| benchmark/corpus/profiling helpers | Called legacy helper directly | `position_identity_key` |
| learning diagnostics/openings/self-play/arena | Called legacy helper directly | `position_identity_key` |
| native adapter/reference/differential diagnostics | Called legacy helper for current state | `position_identity_key` or `repetition_identity_key` |
| `native/semantic.py` | Native exact-key bridge | Retained as the Native implementation and parity boundary |
| `core/keys.py`, package re-export | Legacy/semantic primitives | Retained as compatibility wrappers; no local dispatch |
| tests and frozen fixtures | Direct helper calls | Retained where they explicitly prove legacy compatibility or Python/Native parity |

## Search audit result

After migration, a repository search of `generic_chess/**/*.py` finds direct
`position_key()` / `semantic_position_key()` calls only in the authority,
compatibility module, and the Native semantic bridge.  No production consumer
independently chooses legacy versus semantic identity.
