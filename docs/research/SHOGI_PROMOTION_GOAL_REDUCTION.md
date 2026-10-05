# Independent three-ply goal exclusion after width failure

The full use tree has48 public events and43 complete enemy replies; next-ply
width preflight stopped at lower bound135>128. No goal labels were observed.
New premise: derive a COMPLETE geometric no-mate certificate instead of
materializing its over-budget third ply. Keep original report/width unchanged.

For either Pawn-capture root choice, every saved reply has owner0 K/P(or TP),
owner1 K, and owner0 exactly one held R. Enumerate a SUPERSET of all next own
actions: ordinary King moves, Pawn/Gold moves with optional/forced promotion,
and R drops on every empty square. Exclude own-occupied landings and anchor
capture; do not filter own-King safety (superset only gets larger). For every
projected board find one adjacent black-King move/capture with no white attack.
Remove the landing ordinary victim and vacate old black-King square BEFORE
checking attacks. Pure coordinates implement King, P, Gold, orthogonal R rays.
Each recorded escape is also checked using production compiled in_check on
the resulting virtual position. One legal King escape suffices regardless of
other possible drops/declarations; hands do not block that King move. All
superset actions must pass, not just a predicted or selected action.

For each quiet root choice use its already saved enemy R capture of P as a
counterreply. Owner0 then has only a bare King and no hand, so no legal King
move can deliver check: royal adjacency would violate own-anchor safety.
One counterreply excludes forced mate in the fixed window. This covers ALL5
root actions and ALL baseline ties, without assigning eventual WDL/draw.

The source states must match exactly the native/custody/aux/ply2 premises;
12 capture replies,3 quiet counterreplies expected. At ply3 none can reach
500-move adjudication or fourfold repetition; fewer than11 board resources
exclude nyugyoku. Full captured-origin semantics are kept. Zero new public
events/source queries, no model-weight use in labels. Count all coordinate
projections, virtual escape positions and attack checks; existing48/557 events/
enumerations and0.406sec remain charged. Conservative enumeration charge adds
all projected actions and stays5000;15sec cumulative. Failure leaves every
affected goal unknown. This reduces this NEW fixture only, not arbitrary trees.
