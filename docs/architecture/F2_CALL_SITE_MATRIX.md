# F2 search-path history/repetition call-site matrix

This is the pre-implementation Gate B design audit.  The immutable
`GameState`/`legal_successors` path remains the public/reference oracle.  F2
adds one Core-owned `SearchPathRuntime` used only by `run_root_search`.

## Data-plane ownership

| Boundary | F2 decision |
|---|---|
| Session, replay, serialization, UI, diagnostics | Continue receiving immutable `GameState` with full tuple history and external SHA keys. |
| `reference_minimax` | Remains entirely on immutable `legal_successors` and is not optimized through the runtime. |
| AlphaBeta candidate search | Uses one per-search `SearchPathRuntime` rooted from the immutable Session state. |
| Runtime state | Owns mutable current `Position`, ply, occurrence counts, history evidence, terminal result, exact current key, and process-local runtime hash. It is never serialized or shared between workers. |
| Core authority | Runtime performs legal generation, checked semantic binding, position transition, gave-check evidence, and terminal adjudication. AI does not reimplement repetition rules. |

## Child-creation paths

| Search path | Current child creation | F2 push/pop boundary |
|---|---|---|
| Main `negamax` | `legal_successors` or lazy handle materialization | `with runtime.pushed(action)` around every recursive call |
| PVS null-window | Recursive `negamax` child call | Independent push/pop; re-search starts at parent depth |
| PVS full re-search | Second recursive child call | Independent push/pop |
| Aspiration re-search | Re-enters root `negamax` | Root runtime remains unchanged after each iteration |
| In-check quiescence | Legal evasions | Push/pop around each evasion |
| Ordinary quiescence | Noisy legal children | Core runtime preview/classification, then push/pop |
| Root tactical scan | Root children for mate/evaluation fallback | Push/pop around each root child |
| Lazy/eager tuning modes | Existing modes currently choose handles vs eager states | Runtime owns both results; ordering/action set remains equivalent and no child tuple is retained |
| Cancellation/budget/exception exits | Any recursive branch | Context manager `finally` restores exact parent frame; root exit asserts depth/push-pop balance |

## State reads

| Read | F2 source |
|---|---|
| Position/evaluator/orderer | Runtime search-state view backed by current immutable `Position` |
| Ply / terminal score | Runtime current fields |
| Ordinary repetition | O(1) current exact-key occurrence count |
| Continuous-check loss | Core terminal helper asks runtime for the bounded current repetition cycle only when the limit is reached |
| Search/TT identity | Runtime exact current stable key plus persistent collision-safe repetition snapshot; Standard-Shogi TT remains disabled |
| Exact external key | F1 authority, never replaced by runtime hash |

## Runtime identity and collision boundary

The runtime hash is a deterministic two-word, 128-bit process-local value.  A
root value is built from domain/ruleset, side, board cells, hands, and the
canonical F1 auxiliary components.  Legacy board/drop transitions update it by
XORing only changed component tokens; semantic transitions use the exact
component delta fallback and count it separately.  Every hash bucket keeps
exact external keys, so a forced hash collision cannot merge repetitions.

## Immutable oracle and deferred work

The existing immutable Core transition and `reference_minimax` remain the
correctness oracle.  F2 does not change evaluator values, TT policy,
replacement/score normalization, native production search, or AlphaSho.  F3
will separately define safe Semantic TT reuse; the F2 runtime hash is not a
Semantic TT key by itself.
