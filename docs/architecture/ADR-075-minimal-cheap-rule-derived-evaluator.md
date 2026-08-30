# ADR-075: F24A minimal cheap RuleSet-derived evaluator probe

## Status

F24A is complete as an audit-only signal probe. The micro cost gate, formula
contracts, type-name invariance, mixed-mechanic applicability, hot-path audit,
F22 provenance hashes, v1 harness parity, fixed-time gates, and fixed-node
execution all ran. The 2048-node quality gate did not pass: candidate top-1
delta was `0`, below the required `v1 + 2`, although the frozen controls
passed. The next boundary is
`F24B_MIXED_MECHANIC_RULESET_CERTIFICATION`; production v1 remains the
baseline and no promotion is authorized.

## Frozen formula

The candidate has exactly four concepts:

1. `material_and_inventory`: signed board current-type values and signed hand
   counts from the normalized static profile;
2. `rule_derived_positional_capability`: non-anchor piece value multiplied by
   normalized empty-board mobility capability;
3. `bounded_anchor_structural_space`: bounded occupancy fraction over the
   anchor's precomputed empty-board targets;
4. `promotion_and_drop_structural_capability`: bounded promotion ratio for
   on-board unpromoted pieces plus bounded drop freedom/mobility for hands.

The evaluator builds the normalized profile and all lookup tables once. A
leaf call performs one board scan, one hand-entry scan, bounded static lookups,
and occupancy checks over precomputed anchor targets. It does not enumerate
legal actions, inspect attacks/checks, generate successors, use history or
search state, or run tactical continuation. Perspective is player-0 raw
score, sign-flipped for side to move 1, with deterministic integer rounding.

## Evidence and gates

The frozen F23Y descriptor ledger contains 48 states, including 40
`SHOGI_LIKE` states (10 roots and 30 canonical children) plus 8 generic audit
states. The exact full descriptor SHA-256 is
`1d5797b6f9c0284d61961b9cb144bd45cea828b572c785162989dc472804fe9c`.
The micro gate is candidate median at most `2.0x` v1 and p95 at most `3.0x`;
F24A recorded approximately `0.079x` and `0.085x` respectively.

After that gate passed, the existing v1 parity, fixed-node, fixed-time, and
2048 quality gates were applied without relaxation. Parity and fixed-time
passed; the quality threshold failed at top-1 delta `0`. Root rank remains
unavailable and playing-strength evidence is `NOT_RUN`. The result is valid
real-game benchmark evidence but not a license for coefficient fitting,
AlphaSho supervision, self-play, or production replacement.

## Scope and preservation

The implementation is confined to the audit script, its fixture, this ADR,
and regression tests. F23Z/F23Y/F23X/F23W/F23V and V1–V12 evidence remains
read-only and byte-identical under the repository's normalized line endings.
`master` remains locked, and promotion remains `HOLD` pending explicit Chat
approval bound to an exact candidate SHA.
