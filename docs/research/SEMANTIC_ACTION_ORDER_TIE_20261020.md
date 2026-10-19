# Semantic action declaration order and AlphaBeta ties — 2026-10-20

## Question

Can reversing behavior-equivalent semantic action declarations change a public
AlphaBeta result, and does that demonstrate a search correctness or utility
problem?

## Bounded probe

`semantic_action_order_tie_20261020.py` builds a 5×5 semantic-only ruleset with
two horizontal actions (`east`, `west`) for one type. It compares the original
action tuple with its reversal on the same board (two immobile anchors, three
identical movers). The visible legal mover-action set is identical in both
variants. A deliberately flat evaluator makes every completed leaf score zero;
the probe therefore isolates deterministic ordering and makes no strength
claim. TT, native legality and root-tactical fallback are disabled; public
AlphaBeta limits are qdepth 0.

Reversing the declarations changes the compiled pattern IDs (`sem_00_east` vs
`sem_00_west`) and changes the ruleset fingerprint. At a complete depth-2
search, both variants use 10 nodes and score 0, but select different tied
visible actions (`a3-b3` vs `c3-b3`). At max depth 3 with a 16-node cap, both
complete depth 2 then stop at the cap; each returns its own depth-2 tied action,
score 0, and 16 nodes. The complete legal visible-action sets match.

The source explains the behavior: `MoveOrderer.order` uses `str(action)` as the
last sort key; semantic action strings include compiler pattern and geometry
IDs; the compiler derives semantic pattern IDs from declaration indices.
`compute_fingerprint` hashes the serialized semantic fields, preserving the
declaration sequence. Thus these are distinct compiled rule identities, even
though this fixture gives them the same visible transition set and values.
Existing documented behavior promises a deterministic canonical-string
tie-break for a fixed ruleset, not invariance across separately fingerprinted
encodings. ADR-015 intentionally retains binding identity when coordinates
alone would collapse distinct actions.

## Decision

This is declaration-sensitive exact-tie selection, not a demonstrated value
loss, search defect, or violated compatibility contract. No code/default or
new canonicalization policy follows. Keep the result as a known limit: a
different but behavior-equivalent source ordering can choose a different move
when values tie. Revisit only if a real consumer requires cross-encoding action
identity or a fixed-budget probe with a non-tied utility consequence changes a
specific search decision.

Reproduce with:

```powershell
.\.venv\Scripts\python.exe docs/research/semantic_action_order_tie_20261020.py
```

## Evidence and limits

- Reproduction source: `semantic_action_order_tie_20261020.py`.
- Machine-readable results: `data/semantic_action_order_tie_20261020.json`.
- Relevant implementation: `generic_chess/ai/alphabeta/ordering.py`,
  `generic_chess/core/actions.py`, `generic_chess/rules/compiler.py`, and
  `generic_chess/rules/schema.py`.
- Contract references: `docs/alphabeta_design.md` and
  `docs/architecture/ADR-015-semantic-public-action-binding-and-canonical-aux.md`.

The fixture is synthetic and uses a flat evaluator. It verifies the tie
mechanism and finite result contract only; it does not measure utility, natural
profile frequencies, competitive strength, or invariance over the complete
generated-rule domain.
