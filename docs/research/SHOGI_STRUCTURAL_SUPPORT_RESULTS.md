# Physical support equality: conditional theorem, not admission

The frozen metadata preflight in `data/shogi_structural_support_20261006.json`
failed on a `frozenset` while recording promotion masks. Both compilations had
already run and their rule fingerprints compared equal. No pattern/profile
comparison completed. The two-compilation cap is exhausted; no corrected rerun
or new graph construction is authorized by this result. The failure is evidence
about the recording boundary, not evidence of unequal movement support.

## Compiler relation established from pinned source

`compile_ruleset_for_execution` calls `compile_semantic_ruleset` on semantic
rules and constructs `ExecutableSemanticRuleset` with exactly its `ir`,
`_legacy_compiled`, and `support` objects. This is object reuse within ONE call;
it does not prove equality between independent compilations with arbitrary
environmental capabilities. Standard Shogi's only explicit semantic action
replaces Pawn drops. `_matching_replaced_legacy_patterns` restricts that selector
to drop geometry. Ordinary board templates originate in `lower_legacy_to_ir`:
singleton actor type, singleton atom geometry, inherited masks, empty/enemy
targets, ordinary source-to-target move, and opponent target removal on capture.
The geometry catalog records the same singleton type in `atom_source`.

This source argument explains why the intended signature checks are plausible.
It is not a successful execution of those checks. In particular, the failed
record does not qualify all 13 runtime profile tables or owner 1.

## Equality obligations

For a compiled instance meeting BOTH constructors' strict board-pattern checks,
suppose every selected pattern has a singleton actor matching every selected
`atom_source`, inherited promotion, no guards/zone/slot/postcondition effects,
and ordinary leap or clear ray geometry. Require each candidate path to contain
distinct interior squares and exclude its source and landing square. Require
identical compiled support, canonical geometry and declared profile closure.

Condition on the moving source being own, a fixed own blocker b, one passive
enemy d, and otherwise empty squares. For a quiet candidate s -> u, both
representations accept exactly when u differs from b and d and its interior
path avoids b and d. The source is vacated; it is not a persistent blocker.
For a capture candidate s -> d, both accept exactly when its interior avoids b
and d. The cube's target-enemy literal is satisfied by the same designated d.
The old mask is the sum of distinct path bits, hence equals their Boolean union.
Distinctness is necessary: repeated squares would make arithmetic addition
carry into another bit, while cubes deduplicate literals.

PhysicalProfileEventCubes temporarily sets promotion mode to NONE only while
extracting occupancy; its successor profiles come from the SAME pinned
SharedContactPrefix._variants. This preserves base/current/promoted identity,
allowed/forced masks and alive-result mobility. Capture is absorbing at first
target removal; merging capture cubes does not choose a later profile. Quiet
successors retain that profile. Unions over duplicate atoms preserve support.
Thus one-step support agrees under these assumptions. Induction gives identical
virtual reachability and shortest distances; demand-law averages can reuse the
old distances without a second BFS. This is a conditional semantic proof, not
an independently implemented coordinate check or full-game legality proof.

## Consequence and next action

The old full-distance and independent-coordinate reports remain valid. R/TR's
previously admitted new-constructor evidence remains unchanged. This attempt
does NOT expand empirical admission to the other 11 modes or owner 1, nor to
held drops, royal safety, declarations, history, compound actions, explicit
promotion or typed/stateful guards. Keep those qualifications separate.

A future metadata check must have a separately reviewed question and budget,
retain this failed attempt, compare native Python values before recording, and
serialize sets with an explicit canonical representation. It must not overwrite
the frozen producer/record or present additional compilations as a correction
within an unused budget. Meanwhile the next useful direction is the downstream
goal-certificate boundary rather than another full support rebuild.
