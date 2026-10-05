# Local replay needs complete choices and a literal mate goal

New integration question after the export-layout audit: can the existing public
observer consume source strategy hints without silently changing its goal or
claiming a partial reply list is complete? Source pn/dn, PV, hash and compressed
mate leaves remain untrusted hints. No engine/build/export/labels admitted.

PublicGame covers local Session wins, including a successful nyugyoku WIN claim.
That is useful for unrestricted local WDL, but it is NOT literal checkmate.
Existing observe cannot censor declaration status strings through its enum-only
censored_statuses. Therefore direct PublicGame use is insufficient for a
checkmate-only import. A separate research-only MateOnlyPublicGame delegates
fresh status validation, complete actions and successors to PublicGame, then
marks every non-checkmate terminal/claim unresolved. It never deletes claims,
continues a terminal state or replaces a compressed source node with terminal
mate. CHECKMATE retains its authoritative winner; ongoing depth frontiers and
resource cuts stay unknown. A positive range extreme certifies a mate strategy
within the replay depth; failure/unknown is not a source-independent nonmate.

Strategy guidance may ONLY reorder the complete local choice stream. At an
attacker node a proved maximum/minimum range extreme permits remaining choices
to be skipped by the existing observer. At defender nodes the opposite actor
must have EVERY legal reply covered unless an already-proved adverse extreme
rejects the strategy. A filtered reply generator that exhausts normally would
be mistaken for complete: a missed countercheck or underpromotion can produce
a false positive. Do not represent a source PV as an exhaustive PublicGame.

Future adapter obligations before any source-root use: freeze root selection,
full history/rules conversion and proposed actions; match locally generated
lossless action identities including promotion/drop and declarations; reorder
without filtering; account for all enumeration during hint matching, retain
unmatched hints as diagnostics; apply actual local successors and terminal
before source annotations; identify states by full board/base/current/hands/
actor/history, not board hash alone; decrease remaining horizon at every move.
Unavailable continuations remain unknown. Source compressed child_num0 or
mate_1ply can guide reconstruction, never authorize fake terminal nodes.

The small wrapper adds no search, transport or scheduler. Source export remains
unadmitted. Tests exercise real existing nyugyoku claims for both owners without
board transitions, stale-cache rejection and ordinary terminal/unknown mapping.
This qualifies a missing goal gate, not a new independent mate label or general
official Shogi adjudication. No old window is deepened or budget reset.
