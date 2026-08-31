# ADR-086: Generic declaration/claim semantics

Status: accepted for F26 foundation

## Decision

An optional `RuleSet.declarations` collection describes action-independent
player claims. A `RuleDeclaration` binds a stable ID and owner to reusable
`RuleStateGuard` predicates, an optional exclusive ply limit, an optional
`RuleWeightedMaterialMetric`, ordered score bands, and a configured failure
outcome. The vocabulary is generic: `WIN`, `RESTART`, and `LOSS`.

Declarations are assessed through `assess_declaration()` and listed through
`available_declarations()`. They are not `Action` values, are not legal moves,
do not change side-to-move, and do not participate in terminal or search
evaluation in F26. Compiled declaration data is immutable and is carried in
the compiled semantic IR; runtime does not reread a high-level `RuleSet`.

The weighted metric filters by logical owner, compares base or current type
IDs, applies deterministic integer weights inside an optional compiled zone,
and may include matching base-type hand inventory. It has no traditional-game
knowledge. Action-bound square references fail closed at declaration compile
time.

## Standard-Shogi certification copy

The audit-only certification definition uses mirrored absolute enemy-camp
zones. It requires the declaring side's king in that zone, at least eleven
declaring-side board pieces there (the king plus ten additional pieces), no
check, and `ply < 500`. Its metric scores base-family IDs, gives rook and
bishop five, other nonking families one, excludes the king and opponent, and
includes the declaring side's hand. Bands are `>=31 WIN`, `>=24 RESTART`, and
otherwise `LOSS`. The production Standard-Shogi builder remains unchanged in
F26, so its product fingerprint and F25 search/Native baseline remain stable.

The authoritative rule reference is Japan Shogi Association Article 9 with
the correction effective 2025-10-01; the older 28/27 FAQ variant is not used.
The official 500-move impasse/no-contest rule and administrative restart
procedure remain a separate product boundary, so full-rule readiness remains
false.

## Corrective integration

`TerminalStatus.PERPETUAL_CHECK` now maps to `SessionStatus.PERPETUAL_CHECK`,
preserves the Core winner, and renders both the winning and losing side. The
ordinary repetition mapping remains a draw. No Shogi-specific session branch
was added.
