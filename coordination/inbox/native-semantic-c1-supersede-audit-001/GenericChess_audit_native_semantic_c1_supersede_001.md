# GenericChess Native Semantic C1 Supersede / Runtime Publication Audit 001

Target sandbox SHA:
`9779d5d5dfbbadb38879f75ea396f60c7f78c784`

Active task:
`native-semantic-runtime-search-002`

## Verdict

**C1 supersede: APPROVED**

**Internal runtime state at 9779d5d: CONDITIONALLY ACCEPTED FOR PUBLICATION WORK**

**Final task completion: NOT YET PASS**

This approval explicitly authorizes the phase transition that the Agent correctly refused to perform without authority.

The old ADR-017 / Phase 1.9C-1 compile-only boundary was a real frozen contract. It must not be silently violated or rewritten out of history. However, its compile-only/public-capability restrictions are now authorized to be superseded by the next runtime contract because the prerequisite runtime implementation and differential evidence are sufficiently mature.

Continue immediately in the existing sandbox. Do not stop after applying this authorization. Complete the active TASK to its full definition.

## 1. Formal supersede authority

You are explicitly authorized to supersede the following Phase 1.9C-1 restrictions from ADR-017:

- `semantic_position_state = False`
- `semantic_s0_s4_executor = False`
- `CompiledSemanticIR.capabilities.native_executable = False` as an unconditional C1-era claim
- the C1 prohibition on public semantic position / legal / make / perft / terminal / search entry points

This is **not** authorization to discard ADR-017.

Create a small successor architecture record/spec, e.g. `ADR-018 Native Semantic Runtime and Fixed-Depth Search Contract`, which:

1. states that ADR-017 remains authoritative for deterministic semantic payload/type/pattern/geometry identity, C-owned `GCSemanticRules`, exact 64-bit semantic action layout, closed enum codes, fail-closed size/domain limits, legacy structure non-aliasing, and no high-level RuleSet/game-name execution authority;
2. explicitly supersedes only the C1 compile-only/public-surface/capability restrictions;
3. records the accepted prerequisite chain: payload ABI hardening at `38c554a...`, standard build closure at `d2faa66...`, runtime publication audit target `9779d5d...`;
4. defines the public runtime/search capability gates below.

Do not rewrite old ADR history to pretend C1 always allowed execution.

## 2. Previous audit blockers now closed

Accepted closed at `9779d5d`:

- Ruleset-position binding: `GCSemanticPosition` owns the rules fingerprint and public rules+position APIs reject mismatch.
- Unicode canonical-key parity: Native canonical JSON emits `ensure_ascii=True` compatible escapes, including non-BMP surrogate pairs.
- Exact repetition identity: full SHA-256 is stored as four 64-bit words; lo/hi is legacy compatibility only and non-terminal-eligible.
- Recursive runtime structure: internal C action buffer, trusted make/unmake, terminal-aware recursion, full-history propagation, exact action identity, multi-seed/multi-fixture differential.

Do not regress these while publishing the final API.

## 3. BLOCKER — fix semantic evaluator board identity

Current semantic material search code uses `profile->board[piece->base_type]` for on-board pieces.

That conflicts with established GenericChess evaluation authority:

- board value -> **current type**
- hand value -> **base type**

Required fix:

- on-board piece: `board_values[piece.current_type]`
- hand piece: `hand_values[base_type]`
- deterministic fallback follows the same distinction.

Update the Python brute-force/minimax oracle too; it currently mirrors the incorrect base-type board lookup.

Add a promoted/transformed-piece regression where base/current differ and their board values differ strongly. Search/evaluation must use current type on board; held pieces must continue using base identity.

This must be green before the final search API is declared complete.

## 4. Public terminal API — explicitly authorized

Register a production public Native semantic terminal API.

Expose at least:

- `ongoing`
- `checkmate`
- `stalemate`
- `repetition`
- `max_ply`
- winner `0 / 1 / None`

Requirements:

- reject rules/position fingerprint mismatch;
- require exact full repetition history when history is non-empty;
- preserve Python SemanticEngine precedence: checkmate/stalemate before repetition before max-ply;
- keep S4 reply probes independent of repetition/max-ply/history.

Add direct public differential regressions for all five statuses. Do not use `probe_search()` as the public terminal oracle after `semantic_terminal` exists.

## 5. Public fixed-depth search API — explicitly authorized

Promote the current internal/probe AlphaBeta into the final fixed-depth semantic search API after fixing §3.

Prefer an explicit stable name such as `semantic_fixed_depth_search` unless an existing frozen naming contract says otherwise.

Requirements:

- fully Native recursive hot path;
- Native semantic legal action generation;
- internal C action buffers;
- trusted make/unmake;
- semantic terminal/mate/draw authority;
- stable generic board/hand evaluation profile keyed by `native_rules.type_ids`;
- deterministic exact packed best action;
- exact packed legal PV;
- deterministic tie-break;
- no Python callback at search nodes.

The old `semantic_probe_search` may remain as a lower-level/test compatibility API if useful, but final capability must point to the production fixed-depth API.

Add Python minimax differential tests at depth 1–3 covering ordinary semantic, Cannon, Castling, En Passant if present, Nifu/drop, promotion, S4/Uchifuzume, terminal cases, and the current-type evaluation regression.

Replay PV step-by-step and verify every exact action is legal at that child.

TT remains optional; do not add unsafe TT merely to finish this task.

## 6. Capability transition — authorized only after final gates are green

After public runtime tests are green:

`semantic_position_state = True` is authorized if strict pack/snapshot/key/history, fingerprint binding, malformed-state rejection, and make/unmake restoration are green.

`semantic_s0_s4_executor = True` is authorized if exact legal action parity, S0–S4, attack/check/invariants/postconditions, effects/triggers/promotion/drop, make/unmake, terminal, perft, and randomized differential are green.

For `CompiledSemanticIR.capabilities.native_executable`, do **not** blindly set it globally true. Define it as a per-ruleset fail-closed statement: all primitives present in that compiled semantic ruleset are supported by the Native runtime contract.

Current high-level compiler already rejects `location=hand` state guards; do not invent support merely to make the flag true. Unsupported/future primitives must keep `native_executable=False` or fail the Native-executable path.

Add capability regressions for supported current S0–S4 rulesets and unsupported/future/manual malformed cases.

## 7. Differential closure before COMPLETE

Keep and extend the existing randomized closure suite.

After public terminal/search registration add direct comparisons at sampled states for terminal result, in-check/relevant attack authority where practical, exact PV replay, and search score/best-action differential.

Ensure failures identify fixture, seed, ply, position identity and missing/extra exact actions where relevant.

## 8. Final verification

Before returning COMPLETE, run and report real results for at least:

1. Zig Native build;
2. standard setuptools/wheel build smoke;
3. semantic payload ABI focused tests;
4. semantic position/runtime focused tests;
5. randomized closure differential;
6. final semantic search tests;
7. legacy Native focused regressions;
8. full pytest suite if locally practical.

Do not turn capability flags on before these gates.
Do not modify master.
Push the final sandbox SHA.
Worktree must be clean.

## 9. Execution control

This AUDIT resolves the current hard blocker.

The active task is no longer HARD_BLOCKED by C1.
Resume `native-semantic-runtime-search-002` immediately.

Do not return merely after adding ADR-018, registering terminal, fixing evaluator, registering search, flipping capabilities, or one focused suite passing.

Continue until the full active TASK is COMPLETE, or a new genuine hard blocker outside this granted authority is encountered.

The final response should be the completion report requested by the original TASK.
