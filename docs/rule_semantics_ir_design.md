# Rule Semantic IR Design (Phase 1.9A-2)

Design-only phase.  Nothing here is implemented; production semantics are
untouched.  The Phase 1.9A-1 ownership contract remains in force
(`docs/rule_semantics_architecture.md`); no contract amendment is required.

## 1. Purpose

Design a **finite, typed, declarative, bounded, statically analyzable,
compilable** Generic Rule Semantic IR that can describe, at design level,
Xiangqi cannon, chess castling, chess en passant, shogi nifu and shogi
uchifuzume — plus counterexample "weird" rules — **without any
game-specific primitive**.  The IR is not a scripting language: no Lua, no
Python callback, no arbitrary AST evaluator, no unrestricted bytecode VM.

## 2. Design principles

* Compile-time answers: reads, writes, legality stratum, trial-make need,
  attack need, legal-reply-probe need, hash impact, undo impact, rough cost.
* A primitive that cannot be statically classified is rejected by default.
* Executors never see game names; only compiled type ids, relations,
  predicate kinds, effect kinds, slot ids, zone ids and owner-relative
  selectors.
* No per-node Python callback; no unbounded legality recursion; no
  unbounded effect list; no runtime heap in the native search node.

## 3. Semantic categories (final)

1. **Candidate geometry** — where an actor can geometrically go (leap/ray/
   drop origin), owner-relative, bounded/unbounded.
2. **Target predicate** — occupancy/owner condition of the destination.
3. **Path predicate** — occupancy condition along source..target.
4. **State query guard** — pre-action predicate over piece selectors
   (nifu file query).
5. **Slot guard** — pre-action predicate over auxiliary state (right/token).
6. **Action intent** — actor, source/drop origin, target, chosen promotion,
   semantic parameters.
7. **Bounded effects** — the transition an intent produces (≤ 4 effects).
8. **Auxiliary state** — typed right/token slots with compile-time lifetimes.
9. **Invariant** — post-transition safety (own-anchor-safe; transit squares).
10. **Postcondition** — after-action condition (opponent checked;
    no legal reply).
11. **Bounded legal-reply probe** — stratified existence-of-reply query.

## 4. Proposed compiled semantic representation

Conceptual schema (field-level; names are proposals):

```
CompiledMovePattern:
    geometry: tuple[GeometryAtom]        # leap | ray (+ max_steps)
    target: CompiledTargetPredicate
    path: tuple[CompiledPathPredicate]
    guards: tuple[CompiledStatePredicate]
    slot_guards: tuple[CompiledSlotQuery]
    effects: tuple[CompiledEffect]       # cardinality <= 4
    invariants: tuple[str]               # own_anchor_safe | squares_not_attacked
    postconditions: tuple[CompiledPostcondition]  # <= 2
    cost_class: C0..C4
    stratum: S0..S4
    slot_refs: tuple[slot_id]            # declared slots this pattern touches

CompiledPathPredicate:
    kind: path_clear | path_count_eq | path_count_range
        | path_first_blocker_owner | path_last_blocker_owner
    count/lo/hi: int | None
    owner_filter: self | opponent | any

CompiledStatePredicate:
    aggregation: exists | count
    selector: {owner, type_mode(base|current|any), promoted(yes|no|any),
               location(board|hand), spatial(same_file|same_rank|zone|exact|
               adjacent|path_between)}
    comparison: eq|ne|lt|le|gt|ge
    value: int

CompiledEffect:
    kind: move|remove|remove_from_hand|place|set_current_type|
          clear_right|set_token|clear_token|shift
    square_ref: target|source|token|partner_square
    slot_id: int | None
    type_id: compiled_type_id | None

CompiledAuxSlot:
    slot_id: int
    kind: right | token_square
    lifetime: persistent | expire_next_turn

CompiledPostcondition:
    kind: opponent_checked | no_legal_reply
    probe_stratum: S3            # stratified probe bound
```

All fields are statically typed and bounded; the structural prototype in
`experiments/rule_ir_design_prototype.py` implements exactly this schema
and validates every stress test and counterexample rule against it.

## 5. Geometry model

`leap(offset)` and `ray(direction, max_steps)` remain the geometry
primitives (owner-relative).  Geometry describes **candidate structure
only**: which squares form the path.  Occupancy legality is deliberately
kept out of geometry (target/path predicates own it).

## 6. Path predicate model

A small closed path-occupancy algebra — **no arbitrary path expression**:

* `path_clear` — zero occupied intermediate squares;
* `path_count_eq(n)` — exactly n occupied intermediate squares;
* `path_count_range(lo, hi)` — n in [lo, hi];
* `path_first_blocker_owner(filter)` / `path_last_blocker_owner(filter)` —
  owner filter on the first/last blocker.

This is sufficient for cannon (quiet=clear, capture=count_eq 1) and the
weird-ray counterexample (capture=count_eq 2), and deliberately excludes
general predicate composition.

## 7. Target predicate model

`target_empty`, `target_enemy`, `target_friendly`, `target_any` — separate
from path predicates so the C executor never guesses "capture yes/no" from
the action shape.

## 8. State query model

Typed selectors: owner relation (`self|opponent|any`), type mode
(`base|current|any`), promoted (`yes|no|any`), location (`board|hand`),
spatial (`same_file|same_rank|zone|exact|adjacent|path_between`);
aggregation limited to `exists|count`; comparison ops
`eq|ne|lt|le|gt|ge`.  Every operator is justified by a real rule
(nifu: count + same_file + base + promoted=no; zone-capacity weird rule:
count + zone).

## 9. Action model

**Decision: `Intent + bounded EffectList`** (ADR-6).

* Intent: actor selector, source/drop origin, target, chosen promotion,
  semantic parameters.
* Effects: a fixed-capacity small record (max **4** effects/action), never
  a per-node heap list.

Alternatives compared:

| option | expressiveness | serialization | native packing | make/unmake | search cost | validation |
| --- | --- | --- | --- | --- | --- | --- |
| A. fixed extended record (move + optional second move + optional off-target capture + token delta) | castling/en-passant OK; compound rules awkward | simple | simple | simple | small | small |
| B. bounded EffectList (preferred) | all stress tests + compound moves | simple | fixed-capacity 4 | uniform | small fixed | static cardinality check |
| C. unbounded dynamic list | anything | complex | heap per node | complex | heap | unbounded — rejected |

Preferred because B uniformly covers castling (2 moves + right clear),
en passant (move + off-target remove), compound shift (move + shift) and
drop (hand remove + place) with one small fixed record, at the cost of a
static cardinality bound.

## 10. Effect model

`move, remove, remove_from_hand, place, set_current_type, clear_right,
set_token, clear_token, shift` — closed set, each with a square reference
(target/source/token/partner_square) and optional slot/type parameters.
Promotion is modeled as `move + set_current_type` (kept as one option; the
existing compiled masks remain the single promotion-authority source for
*which* promotion is allowed).

## 11. Auxiliary state model

Two accepted kinds (ADR-7):

* **right** — persistent bool, cleared by `clear_right` (castling right,
  once-per-game permission);
* **token_square** — square-or-none, set by `set_token`, expires at the
  next turn boundary (en-passant opportunity).

Counter/bounded-use slots are deferred (no present stress test needs them).
Slots are typed (`slot_id, kind, lifetime`), compile-time fixed
(≤ 8 per ruleset), and never Python objects in a position.  A
**uniform turn-boundary lifecycle step** (expire tokens) runs once per
transition in both executors — deterministic and undo-simple — rather than
emitting per-action expiry effects (which would let RuleSet field order
change semantics).

## 12. State ownership / hash / undo

Every slot satisfies the ten-point State Contract (definition, Python
storage, native storage, serialization, identity, hash, make, unmake,
repetition interaction, TT safety — see `state_model.json`).  Slots enter
position identity: two positions that differ only in a right/token have
different future legality, therefore different `position_key` and native
hash (slot-id Zobrist contributions; incremental, never full rehash after
an action).  Undo uses a fixed expanded snapshot of changed slots in
`GCUndo`-style records (see §24).

## 13. Legality strata (ADR-8)

```
S0  Geometry / Occupancy
S1  State Query / Rights / Tokens
S2  Pseudo Attack (geometry + occupancy + path predicates; NO trial make)
S3  Trial Transition + Global Invariants (own-anchor safety)
S4  Bounded Post-Action Probe (stratified; probe stratum <= S3)
S5  Terminal / History
```

Allowed edges: `S1→S0`, `S2→S0/S1`, `S3→S0/S1/S2`,
`S4→S0/S1/S2/S3`, `S5→S0..S3`.  The graph is a DAG; the compiler rejects
any edge that violates it.

## 14. Semantic dependency graph

```
geometry ──► candidate ──► target predicate ──► path predicate
                                   │
                                   ▼
                          state/slot guards (S1)
                                   │
                                   ▼
                      trial make + invariant (S3)
                                   │
                                   ▼
                    postcondition / reply probe (S4)
                                   │
                                   ▼
                              terminal (S5)
```

No edge goes upward; no cycle is expressible.

## 15. Bounded legal-reply probe (ADR-9)

`EXISTS_LEGAL_REPLY(stratum=S3)` is the only probe primitive.  It answers
"does the opponent have at least one legal reply" by running the *reply
side's* candidate generation, cheap guards, trial make and invariant — **up
to S3 only**.  Nested S4 postconditions are disabled inside the probe
(stratified probe mode), so:

* probe depth is **exactly one level** (statically bounded);
* recursion `legal → terminal → legal` cannot occur;
* the probe is an existence scan with early exit (first valid reply).

**Uchifuzume termination model** (Option B, recommended): a drop whose
postcondition is `opponent_checked + no_legal_reply` runs the probe on the
child position with S4 disabled for the reply side.  This is statically
finite and compilable.  Trade-off: the exotic corner where the opponent's
only replies are themselves postcondition-forbidden (a reply that would
itself be a drop-with-no-reply) is treated as "has reply" (approximation).
Option A (full recursion) is semantically exact but has no clean static
termination proof (recursion depth is bounded only by finite material);
Option C (specialized evasion probe) is not generic.  B is recommended;
A is documented as a possible future refinement with a material-bounded
termination proof, gated behind the same `probe_stratum` knob.

## 16. Static cost model (ADR-11)

```
C0  compile-time only
C1  O(1) per candidate
C2  small board/path scan (bounded by path length / board)
C3  trial-make + attack
C4  bounded legal-reply probe (stratified)
```

Every primitive is tagged at compile time; native executes cheap-first.

## 17. Guard ordering

The compiler **pre-orders guards by cost class** (cheap first), independent
of RuleSet field order, then by stratum:

```
candidate → geometry → target/path predicate → state guard →
trial make → royal-safety invariant → rare expensive postcondition
```

RuleSet field order must never decide runtime cost.

## 18. Pseudo-attack interaction

Attack eligibility is **not** "all pseudo destinations".  The IR separates
`quiet eligibility` (path predicate on empty target) from `capture
eligibility` (path predicate on enemy target), and pseudo-attack for
royal-safety uses the **capture eligibility path predicate** (cannon: a
royal behind exactly one screen is attacked).  This keeps attack acyclic
and correct for screen-based rules.

## 19. Geometry single-lowering decision (ADR-10)

Three designs compared:

* **A. Python precomputes all geometry structure; native consumes tables.**
  Compiler emits per-(type, owner, source) ordered path segments and leap
  targets; both executors consume the same tables.  Runtime occupancy
  evaluation is execution, not lowering.
* B. Canonical geometry IR executed by both (shared bytecode-like
  interpreter).
* C. Hybrid (precompute leap, execute ray stepping).

Decision: **A** (precompute geometry structure; single lowering).
Path metadata (segment lists, lengths) is exactly what path predicates
need at runtime; payload size scales as O(types × owners × squares × path
length) which stays small for 16×16 and typical type counts; compile cost
is one-time; native cache locality improves; differential testing is
simpler because both sides consume identical tables.  B adds an interpreter
without benefit; C leaves the ray double-interpretation in place.

## 20. IR versioning (ADR-12)

Four version axes, all independent:

* `RuleSet schema version` — user-facing definitions;
* `Compiled IR version` — the compiled semantic representation;
* `native compile payload version` — the packed C input;
* `checkpoint/ruleset fingerprint` — includes the IR version so old and
  new semantics never collide.

Policy: old serialized rulesets are recompiled additively (see §Migration);
an unsupported IR version is rejected with an explicit error, never
silently reinterpreted.

## 21. Validation vs compiler responsibilities

* **Validation** rejects: structurally invalid rules, out-of-range
  references, type mismatches, dependency cycles, unsupported combinations,
  unbounded effect lists, invalid slot lifecycles, illegal postcondition
  recursion (probe stratum > S3).
* **Compiler** normalizes, assigns ids, lowers selectors, builds path
  metadata, orders guards, allocates state slots, emits deterministic IR.

## 22. Python reference execution plan

```
candidate generation (geometry tables)
→ target/path predicate
→ state/slot guards
→ action effect construction (bounded list)
→ trial transition
→ invariant (own anchor / transit squares)
→ postcondition (incl. stratified reply probe)
```

Readable, correctness-first, no native packing assumptions.

## 23. Native execution plan

Mechanical execution of the compiled IR: no game names, fixed/bounded
structs, no heap allocation in the search node, no Python callback, cheap
guard ordering, uniform effect apply/undo, slot hashing.

## 24. Make / unmake plan

Compare: A) snapshot changed fields, B) inverse-effect log, C) fixed
expanded undo struct.  Decision: **C — fixed expanded undo struct** (the
current `GCUndo` pattern extended with a fixed slot-snapshot array and the
multi-effect fields).  Rationale: inverse logs (B) require interpreting
effects at undo time (slower, more failure-prone); whole-state snapshots
(A) copy too much; the effect bound (≤ 4) and slot bound (≤ 8) make C
small and cache-friendly.  Failure rollback applies the same snapshot
restoration.

## 25. Native ABI impact

Expected breaking changes (future, not now): packed action layout (effects
list), `GCPosition` slot array, `GCUndo` expansion, rules payload (path
metadata).  These should land as **one coordinated ABI transition** in
Phase 1.9B/C rather than per-field bumps; internal-only additions (new
payload keys with default absence) can be additive.  `native_version`
stays `0.3.0` in this phase.

## 26. Generator compatibility

* simple blocker/occupancy predicates: `GENERATOR_SAFE_WITH_STATIC_FILTER`;
* rights/token slots: `GENERATOR_SAFE_WITH_STATIC_FILTER` (bounded slots,
  typed lifetimes);
* compound effects: `PRESET_ONLY_FOR_NOW`;
* post-action legal-reply rules (uchifuzume-like): `PRESET_ONLY_FOR_NOW`.

The generator remains decoupled: it produces high-level Rule Definitions;
compiler assigns IR ids/slots (never the reverse).

## 27. Backward compatibility plan

First-IR implementation must keep all existing rulesets, tests and
serialized rules semantically identical.  Proof plan: existing full test
suite; Python before/after corpus comparison; native differential;
perft equivalence; hash/action serialization regression.  Existing RuleSet
schema is the source for automatic lowering into the IR (migration §28).

## 28. Migration plan

Existing `RuleSet` schema remains the user-facing definition; the compiler
additively lowers it to the IR (leap/ray → geometry + target + clear path;
promotion/drop masks → templates + effects; anchor → invariant).  No manual
preset rewrite.  A schema bump is only required for new high-level syntax
(path predicates, guards, slots); it is additive and old serialized
rulesets keep compiling through the existing schema path.  Migration is
not implemented in this phase.

## 29. Architecture contract amendments

**NONE** — the Phase 1.9A-1 ownership contract and invariants remain in
force.  (I1 moves from PARTIAL to the single-lowering plan of §19, which is
an implementation target, not a contract change.)

## 30. Proposed Phase 1.9B scope

Design only: next phase implements the Python reference semantics for the
IR — which production files may change: `rules/schema.py` (additive syntax),
`rules/compiler.py` (IR lowering), `core/` executor layers, `native`
payload/state/undo/ABI (one coordinated transition).  Frozen: search,
learner, Session/UI ownership, no game-specific semantics.

## 31. ADR summary

* ADR-6 Action representation: bounded effect list (≤ 4), fixed record.
* ADR-7 Auxiliary state: typed `right` / `token_square` slots, compile-time
  lifetime, uniform turn-boundary expiry.
* ADR-8 Legality strata: S0..S5 DAG with fixed allowed edges.
* ADR-9 Reply probe: `EXISTS_LEGAL_REPLY(stratum<=S3)`, single-level,
  early-exit.
* ADR-10 Geometry: single lowering via precomputed path/target metadata.
* ADR-11 Cost model: C0..C4, compiler pre-orders guards cheap-first.
* ADR-12 Versioning: four independent axes; additive migration; explicit
  rejection of unsupported versions.

## 32. Observed

* The structural prototype validates 14 templates (5 stress groups + 5
  weird rules) against the proposed schema: all valid, effect counts ≤ 4,
  cost classes assigned, strata consistent, no game-name tokens in
  execution fields.
* The dependency-cycle template (probe re-entering S4) is rejected.
* Production code does not import `experiments/rule_ir_design_prototype.py`.

## 33. Inferred

* A small closed algebra (geometry + 5 path kinds + 4 target kinds + typed
  selectors + 9 effects + 2 slot kinds + 2 postconditions + 1 probe) is
  sufficient for the five stress tests and five counterexamples — no
  game-specific opcode is needed.
* The stratified probe is the right first-IR compromise: statically
  bounded, compilable, with a documented semantic corner.

## 34. Not established

* Full-recursion uchifuzume equivalence in the exotic corner (needs a
  material-bounded termination proof before adoption).
* Actual native cost of C4 probes (no implementation exists).
* Generator behavior for the new high-level syntax (Phase 1.9B concern).

## 35. Known risks

* Payload growth from path metadata (bounded, but must be measured).
* Coordinated ABI transition is large; must be staged in one phase.
* Stratified-probe corner semantics could surprise in contrived positions.

## 36. Tests

`tests/test_rule_semantics_ir_design.py` exercises the prototype: stress
test mappings, weird rules, no game-name execution tokens, effect
cardinality, typed slots, cycle rejection, forbidden probe rejection, cost
classes, deterministic serialization, and production non-import.

## 37. Performance / audit wall

Prototype validation and artifact generation: < 1 s (measured in
`performance.json` of this phase's run).

## 38. Files

* `experiments/rule_ir_design_prototype.py` (design-only, not imported by
  production)
* `docs/rule_semantics_ir_design.md`, `docs/rule_semantics_ir_stress_tests.md`
* `scripts/rule_ir_design_report.py` (artifact generator)
* `tests/test_rule_semantics_ir_design.py`
* `pyproject.toml` (version `0.8.0a7`)

Production semantics (Core/Rules schema/compiler/native/learner) untouched.

## 39. Git

Commit + push; `HEAD == origin/master`; clean tree; no force push.

## 40. Final verdict

**`RULE_IR_DESIGN_READY_FOR_REFERENCE_IMPLEMENTATION`**

The five stress tests are expressible with a closed generic primitive set;
the action/state models are explicit; auxiliary-state identity/hash/undo
contracts are complete; dependency strata are acyclic; the uchifuzume probe
has a bounded termination model; geometry single-lowering is decided;
native cost is bounded; backward compatibility and migration routes are
defined.  Phase 1.9B may start the Python reference implementation.
