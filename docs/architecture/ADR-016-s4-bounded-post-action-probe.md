# ADR-016 — Python Bounded S4 Post-Action Probe (Phase 1.9B-3)

Status: frozen specification for Phase 1.9B-3

## 1. Postcondition polarity audit (source-confirmed)

Audited: `generic_chess/rules/schema.py`, `generic_chess/rules/ir.py`,
`generic_chess/rules/compiler.py`, `tests/rule_semantics_ir_fixtures.py`,
`experiments/rule_ir_design_prototype.py`, and the design documents.

- Schema: `POSTCONDITION_KINDS = ("opponent_checked", "no_legal_reply")` is
  the closed postcondition set. `RulePostcondition(kind, max_stratum="S3")`.
- Compiled IR: `CompiledPostcondition(kind, max_stratum)`; validation
  rejects `no_legal_reply` with `max_stratum > MAX_PROBE_STRATUM ("S3")` or
  `>= S4` ("probe must be strictly below S4").
- Compiler: `contains_postcondition` capability; today
  `new_ir_core_executable = not contains_post` (S4 rulesets fail closed).
- Fixtures: `uchifuzume_ruleset()` action `drop_no_legal_reply_forbidden`
  and `weird_rulesets()[4]` action `action_class_no_immediate_mate` both use
  `[opponent_checked, no_legal_reply(max_stratum=S3)]`.
- Prototype: `_uchifuzume_template()` ("drop_no_legal_reply_forbidden") and
  `_weird_templates()` restricted ("action_class_no_immediate_mate").

Polarity (frozen): in every existing fixture/prototype the postconditions
act as **prohibitions**: a candidate whose postconditions evaluate true is
removed from legal actions.  In particular, a no-reply checking finish is
**forbidden** (uchifuzume-shaped restriction).  Names never carry
semantics; the truth table below is the only authority.

## 2. Truth table (frozen)

For a candidate that passed S0-S3 trial legality, let:

- `C` = `opponent_checked` postcondition evaluated on the full child;
- `E` = `EXISTS_LEGAL_REPLY(stratum <= S3)` on the full child;
- `N` = `no_legal_reply` postcondition = `NOT E`.

Cost order is fixed: `C` is evaluated first; the C4 reply probe runs only
when `C` is true (or when the pattern contains `no_legal_reply` without
`opponent_checked`).

| `opponent_checked` (C) | `exists_s3_reply` (E) | `no_legal_reply` (N) | candidate legal? |
| --- | --- | --- | --- |
| False | (probe not run) | n/a | YES (S0-S3 decides) |
| True | True | False | YES |
| True | False | True | NO (rejected) |

A pattern containing only `no_legal_reply` (no `opponent_checked`) is
governed by the same table with the C column treated as "not applicable"
(the probe runs unconditionally and `N=True` rejects).

## 3. S4 position in the legality DAG

```
S0 geometry / occupancy
→ S1 guards / aux state
→ S2 pseudo attack
→ S3 trial transition + invariants
→ S4 post-action probe   (this phase)
```

S4 never participates in S0-S3 candidate generation; it is a post-trial
filter only.

## 4. `opponent_checked` (frozen)

For parent `side_to_move = A` and child `side_to_move = B = 1 - A`:
`opponent_checked` is true iff `B`'s anchor in the child is pseudo-attacked
by `A` under the existing semantic S2 pseudo-attack contract
(`in_check(child, child.side_to_move)`).  It is **never** evaluated against
the parent side.  No legacy/game-name logic.

## 5. `no_legal_reply(max_stratum=S3)` / EXISTS_LEGAL_REPLY (frozen)

`EXISTS_LEGAL_REPLY(stratum <= S3)` on the full child asks: does the reply
side (`child.side_to_move`) have at least one S0-S3-legal action?

`no_legal_reply = NOT EXISTS_LEGAL_REPLY(stratum <= S3)`.

The probe reuses the exact same S0-S3 legality machinery as normal
legality with S4 disabled; there is exactly one S0-S3 oracle.

## 6. Exactly-one-level stratification (frozen)

The probe scans candidate → S0 → S1 → S2 → S3 (trial + invariant) and
stops.  Reply actions' own S4 postconditions are **never** evaluated inside
the probe:

```
parent S4 → probe reply S0-S3 → STOP
```

No `parent S4 → reply S4 → reply-of-reply` recursion.

## 7. Option B approximation (frozen)

If the opponent's only S0-S3 reply would itself be forbidden by its own
`no_legal_reply` postcondition under full S4 semantics, it **still counts as
a reply** in the parent probe: `EXISTS_LEGAL_REPLY(S3) = True`, so the
parent's `no_legal_reply` fails and the parent candidate stays legal.
This is the intentional ADR-9 Option B approximation.  Option A
(full recursion) is out of scope for Phase 1.9B-3.

## 8. Probe never enters S5 (frozen)

The reply probe must not call terminal adjudication, repetition logic,
max-ply checks, history, or GameSession results.  It answers only "one
S0-S3 legal reply exists".

## 9. Probe input is the full child (frozen)

The probe input is the complete transition result of the parent action:
board, hands, promotion/current types, side to move, canonical aux state,
`expire_next_turn` lifecycle, transition-trigger results and explicit aux
effects.  Pre-action positions, partial makes or hand-built
approximations are forbidden.

## 10. Early exit (frozen MUST)

`EXISTS_LEGAL_REPLY` is an existence query: the scan must return `True` at
the first S3-valid reply and must not materialize the full reply list.

## 11. Postcondition cost ordering (frozen)

`opponent_checked` is evaluated before the C4 reply probe.  RuleSet source
field order never decides runtime cost.

## 12. Genericity (frozen)

No production branch on pawn/shogi/uchifuzume/drop-mate/chess/xiangqi.
`uchifuzume` appears only as a fixture/stress name.  The executor consumes
only `CompiledPostcondition.kind`, `max_stratum` and the generic semantic
position.  Non-drop restricted finish (board move/capture +
`opponent_checked` + `no_legal_reply`) must work through the same
primitive.

## 13. Capability transition (frozen)

The compiled IR v2 already expresses S4 (closed postcondition kinds,
`max_stratum` validation, `contains_postcondition`); **no IR/schema bump is
required**.  After Phase 1.9B-3, a ruleset using only supported S0-S4
primitives (`opponent_checked`, `no_legal_reply(max_stratum=S3)`) must get
`new_ir_core_executable = True`.  Unsupported postconditions, invalid
`max_stratum`, or probes above S3 remain fail-closed.

## 14. Public Core ownership (frozen)

`initial_state`, `legal_actions`, `apply_action`, `legal_successors`,
`terminal_result` stay the only public lifecycle.  No second public API.
R0/R1/R2/R3 contracts (fingerprint checks, public semantic action
identity, exact geometry binding, canonical aux state) are inherited
unchanged.  An S4 action appears in `legal_actions`/`legal_successors`
only when S0-S3-legal AND all S4 postconditions pass; `apply_action` must
raise `IllegalActionError` for S4-forbidden forged/public actions.

## 15. Phase boundary

Phase 1.9B-3 implements the Python S4 probe only.  Native/Search/Learner/
UI/Session semantic schemas remain frozen and out of scope.
