# ADR-087: Authoritative state context for declaration assessment

Status: accepted for F26 corrective R1

Declaration claims are decisions about a game state, not detached board
positions. The public `assess_declaration()` and
`available_declarations()` APIs therefore require a `GameState`; passing a
bare `Position` raises a deterministic `TypeError` instead of inventing
`ply_count=0`. Assessment first applies the normal ruleset fingerprint match,
then reads the immutable position and authoritative ply context. No state is
mutated.

The audit-only Standard-Shogi certification copy executes Article 9's current
thresholds: 23 is `LOSS`, 24 and 30 are `RESTART`, and 31 is `WIN`. The
exclusive pre-500 control is executable: ply 499 applies the score band,
while plies 500 and 501 return configured `LOSS`. The tests also exercise both
owners, enemy-camp piece count, king zone, check, board-vs-hand scope,
promotion base-family scoring, available-declaration filtering, and a real
continuous-check repetition path through `GameSession.result`.

The production Standard-Shogi builder remains declaration-free and retains its
certified fingerprint. Product/session/search integration remains the F27
boundary; the official 500-move impasse/no-contest rule remains separate.
