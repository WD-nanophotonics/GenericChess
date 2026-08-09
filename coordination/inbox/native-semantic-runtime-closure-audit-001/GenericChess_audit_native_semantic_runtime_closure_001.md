# GenericChess Native Semantic Runtime Closure Audit 001

Target: `20b57e770a643a9cd44d2d7a0c6a3d7cc6adb158`

Baseline accepted before this run: `d2faa66289d4e4290d9d7170f533b985d1b57825`

Verdict: **FAIL / INCOMPLETE FOR TASK CLOSURE**

This is not a rejection of the substantial implementation progress. The candidate contains a real independent semantic runtime, key implementation, checked transitions, guarded action generation, S4 probe, perft, multi-ply differential, and a fixed-depth AlphaBeta probe. The capability flags are correctly still false.

Continue the active `native-semantic-runtime-search-002` task in the current sandbox. Do not reset or discard valid later work. Close the findings below, add regressions, run the required suites, and continue until COMPLETE or genuinely HARD_BLOCKED.

## 1. BLOCKER — semantic position is not bound to its ruleset identity

`GCSemanticPosition` stores board/hands/side/ply/aux/history, but no ruleset fingerprint or equivalent immutable rules identity. Public APIs accept `(rules_capsule, position_capsule)` independently. Therefore a position packed under semantic rules A can later be supplied with semantic rules B, and the position cannot detect the mismatch.

Required:
- bind every `GCSemanticPosition` to the exact semantic rules identity at pack/creation time;
- reject mismatch in every public `(rules, position)` entry point before reading/interpreting state;
- preserve binding through make/unmake/children;
- add regression coverage for snapshot/key/legal/make/perft/search with deliberately mismatched valid rules capsules.

Do not rely only on board size/type count equality.

## 2. BLOCKER — valid Unicode type IDs cannot produce Native canonical keys

Payload v2 accepts normal UTF-8 type IDs and high-level RuleSet validation only requires a non-empty unique Python string; embedded NUL is separately rejected.

Python `semantic_position_key()` canonicalizes with `json.dumps(..., ensure_ascii=True)`. Native `sb_json_string()` currently fails for every byte `>= 0x80`. Thus valid IDs such as `兵`, `é`, or non-BMP Unicode can compile but cannot receive a Native position key matching Python.

Required:
- implement exact `ensure_ascii=True` compatible JSON string escaping for UTF-8 Unicode, including non-BMP surrogate-pair emission where required; OR deliberately narrow the public high-level type-ID contract everywhere with compatibility analysis. Prefer preserving the existing string domain.
- add Python↔Native key parity tests for BMP and preferably non-BMP type IDs.

## 3. BLOCKER — terminal / repetition / max-ply authority is not closed

Python SemanticEngine terminal authority is: no legal + in-check => checkmate; no legal + not in-check => stalemate; repetition threshold => repetition; ply threshold => max-ply; else ongoing.

At this candidate there is no production `semantic_terminal` public API. Native state transports `history_lo/history_hi` pairs and exposes occurrence queries, but there is no demonstrated exact mapping from Python's full SHA-256 repetition-key/count authority to these 128-bit entries.

Required:
- define and implement the exact Native repetition-history contract;
- do not silently truncate a SHA-256 identity to 128 bits if exact equality is the authority;
- implement Native semantic terminal parity for checkmate/stalemate/repetition/max-ply/ongoing;
- add exact Python↔Native terminal differential tests;
- make recursive perft/search respect terminal state where required by the task contract;
- keep the S4 reply probe independent of repetition/max-ply, matching ADR-016/Python authority.

## 4. BLOCKER — current differential suite is substantial but not yet the requested closure proof

Current strengths include exact action-set parity across core fixtures, an 8-ply stress-corpus path, a fixed-seed castling full-state/key comparison, promotion/path_between coverage, S4 root count and perft tests.

Still required:
- multiple fixed seeds;
- randomized legal playouts across the major semantic corpus, not only castling;
- at each position compare exact packed legal set, full canonical child state, position key, in-check/relevant pseudo-attack, and terminal result;
- recursive perft parity at practical depths;
- reproducible failure diagnostics (fixture/fingerprint, seed, ply, state, missing/extra actions, chosen exact action);
- reach the originally requested hundreds+ intermediate-position proof if practical.

Do not turn on `semantic_position_state` / `semantic_s0_s4_executor` merely because the focused suite is green.

## 5. SEARCH — `semantic_probe_search` is accepted as a probe, not final fixed-depth search

The existing probe is useful and its depth-3 Python differential is valuable, but it is intentionally not the final search contract.

Current probe limitations:
- evaluation is `base_type_index + 1`, only a deterministic test heuristic;
- board only, no hand material;
- no semantic terminal/mate score;
- recursive node action enumeration creates/iterates CPython tuple/PyLong objects;
- recursive transitions use copied checked children rather than the trusted Native make/unmake hot path.

Required final search:
- production fixed-depth semantic AlphaBeta only after runtime closure;
- semantic terminal/mate/stalemate/repetition/max-ply behavior;
- generic evaluation tied to stable semantic type identity/profile, with board and hand material according to GenericChess authority;
- exact deterministic best packed action and legal exact PV;
- internal C action buffer/list in recursive hot path rather than Python-object action lists;
- trusted Native make/unmake after legal enumeration/validation;
- Python brute-force/minimax differential on small fixtures including terminal and promotion/drop/S4 cases.

TT remains optional. If added, repetition/search context must make the key safe.

## 6. Capability / executable gate

Current false flags are correct:
- `semantic_position_state = False`
- `semantic_s0_s4_executor = False`

Keep them false until findings 1–4 are closed and runtime parity is proven.

Then define `native_executable` ruleset-specifically/fail-closed. Hand-location state guards are currently rejected by the high-level semantic compiler, so Native need not invent support for them, but malformed/manual payloads must not accidentally create a falsely executable ruleset.

## 7. Non-blocking observations

- Independent `GCSemanticPosition` rather than legacy `GCPosition` is the correct architecture.
- Full-position `GCSemanticUndo` is heavy but acceptable for correctness-first implementation.
- Native pseudo-attack layering appears directionally aligned with Python; keep differential coverage around it.
- Do not remove current probe tests; they remain useful lower-level controls after final search exists.

## Required continuation

Continue the existing active task without an intermediate progress return. Commits/pushes are mechanical persistence only.

Completion still means: Native S0–S4 runtime exact parity + terminal/repetition + multi-step differential + perft + final fixed-depth AlphaBeta/PV/minimax parity + required test suites, with clean sandbox and master unchanged.
