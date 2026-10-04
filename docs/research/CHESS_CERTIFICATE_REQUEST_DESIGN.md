# Local state association before an independent Chess certificate

2026-10-04. Implement only a bounded request encoder; no tablebase/library,
network probe, goal label or operational certificate admission. A source file
name, SHA or caller's premise flags cannot establish state/move equivalence.

Initial scope: exact production Western fingerprint,8x8 square board, at most
5pieces, native Kings and current ordinary N/B/R/Q (native or valid Pawn-origin
promotion), empty hands, ALL four rights explicitly0, EP explicitlyNone, no
foreign/duplicate aux keys. Resource/provenance ledger and current legal state
guards apply. Own side may be in check, previous mover's King may not. Kings
must be nonadjacent. Pawns/EP/rights intentionally remain unsupported rather
than silently erased. They require separate future qualification.

Read fresh local terminal first: a terminal request is rejected and must use
authoritative local goal handling, not a table lookup. Require nonnegative
absolute ply below endpoint; complete history length=ply+1, unique positive
repetition counts equal the history key Counter, and the final history key
equal the current local identity. These checks establish internal association,
not proof all historical moves were legal or reached from the initial array.
Store the ENTIRE original history, counts, aux/provenance, current position and
terminal in a canonical local-state payload with SHA256. Distinct native/
promoted provenance or history can share an external current-board FEN but
must keep distinct request-state hashes. Never change Core identities.

FEN uses owner0=White, file/rank mapping a1=local index0, reversed rank display,
current types, unchanged side, rights/EP absent. Halfmove clock0 is a declared
unused placeholder in DTM-only probing, NOT reconstructed local history;
fullmove field is ply//2+1 and is likewise not the finite endpoint. Preserve
absolute local ply, remaining horizon, rule fingerprint and maximum repetition
count OUTSIDE FEN. No inference of a50-move claim from these placeholder clocks.

The packet says source_verified=false. It cannot satisfy the conditional
bridge's source/state verification premise. A future adapter must verify a
pinned library/file manifest, prove movement/goal semantics in this scope,
associate probe input/result with this exact packet/hash, and retain full local
history/horizon in the conversion. PublicGame's stale terminal rejection stays
active. Foreign RuleSet, malformed history or unsupported source state fails
explicitly; no unknown becomes draw. No source credentials or extra workers.

Independent diagram/owner/provenance/history and rejection controls validate
only serialization/association. python-chess is not installed here and no
external legal-choice differential or probe has run. This fills a concrete
prerequisite; it does not claim an operational independent label source.
