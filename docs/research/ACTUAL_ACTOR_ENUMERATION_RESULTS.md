# Complete actual-actor labels on unchanged Chess and Shogi fixtures

The frozen ACTUAL_ACTOR_ENUMERATION_PROTOCOL.md uses the two physical boards
already stored in nonterminal_physical_support_20261003.json. It never invokes
the focal substitution helper. Exact owner/base/current-type/promoted counts
match compiled initial inventory; both roots have empty hands, owner 0 to move,
quiet anchors and ongoing synthetic-history status. These are unpromoted board
contexts, not reachable-play samples, new representative draws or held actors.

Root actions are enumerated once and grouped by every existing own ordinary
actor's actual source. Every relevant first action and legal opponent reply is
exhausted, including losing/quiet branches after a successful action is found.
Promotion branches remain alternatives of the same root actor. Anchors are
not first actors; their opponent replies remain part of the complete task.

| Game | Actual own ordinary actors | Individually successful actors | Exact reconstructed count |
| --- | ---: | ---: | ---: |
| Chess | 15 | 2 | 2 |
| Standard Shogi | 19 | 1 | 1 |

Only actual Rooks succeed on these two selected contexts. Their marked-actor
means are one; other present base types have zero. These point-mass observations
are implementation evidence, not estimated type values, representative rates
or a reason to set all other material weights to zero. There are no promoted
types initially, so this gives no such type means; absent types must not be
silently assigned zero scores. In particular, nothing is installed in gameplay.

The complete evidence uses 2,107 materializations in 0.703 seconds, including
compilation/validation, within the unchanged 20,000/30-second gate. Full actor
actions, reply counts, first refutations and protocol/program/input hashes are
preserved in data/actual_actor_enumeration_20261004.json. Unlike the earlier
replacement R score, each first actor is already present in actual inventory.

Four focused tests independently compare grouped first-action coverage with
raw-position public action enumeration, replay successful branches and recorded
refutations through public apply_action, verify exact count reconstruction and
deterministic evidence, and reject a one-transition abort or inventory-changing
substitution. Public replays are test work, not included in the recorded audit's
materialization cost. Neither this check nor the earlier abstract certificate
establishes full real-game/official-terminal parity outside the stated scope.

## Decision and next question

Adopt the feasibility result: on these two existing complete actual-inventory
contexts, a single pass can supply compatible labels for all current ordinary
actors at low bounded cost. No type substitution, uniform-source assumption or
physical deletion is needed. This closes that implementation prerequisite;
do not repeat these fixtures to estimate a population or generate more R cases.

The missing ingredient is a reference law with independent motivation and a
distinct deployment law/loss. One possible synthetic reference is uniform
physical placements of unchanged initial inventory, conditioned on intrinsic
structural admissibility and quiet actual anchors. Its motivation would be an
exchangeable uncertainty baseline, not strategic visitation or a uniquely
rule-selected law. It must be specified and checked before use. In Shogi, a
direct product of 57 unpromoted own/enemy Pawn-rank pairs on each file enumerates
all full-inventory nifu/dead-Pawn-free Pawn layouts uniformly when no source is
fixed. Non-Pawn dead placement and dynamic quiet-root conditioning still require
their own exact accounting; naive per-type redraw is not licensed by this fact.

Before numerical scores, determine whether that whole joint reference can be
sampled without hidden source/type conditioning under a small proposal/cost
gate. Reference nonemptiness is witnessed by these actual boards, but their
selection gives no acceptance frequency. Separately predeclare what deployment
inventory variation and capability-count loss would test; fixed initial counts
alone cannot test a static vector's transfer. Do not fit to those labels or
claim count loss is W/D/L, custody, search quality or material validation.
Promoted/hand scope, useful strategic signal and cheap cross-game prior validity
remain open. Xiangqi human values and production evaluation remain unchanged.
