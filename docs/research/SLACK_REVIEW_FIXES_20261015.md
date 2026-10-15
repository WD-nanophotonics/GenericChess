# Slack review fixes and bounded architecture decisions —2026-10-15

User approved this repair BEFORE mainline continuation. This report records
adopted, already-addressed and deferred advice; CHAT_Comments remain suggestions,
not new authority. No new mainline training/game batch was launched by PRIMARY.
Science is OPEN. Historical entry documents are preserved at fixed
4f6858b128e38c3b93360d78b7f5de6ad61af695, not deleted evidence or active queues.

## Actual Native defect and repair

Dot's supplement1792050152 supplied a static witness, then PRIMARY executed it:
western_chess, max_ply3, RuleAutomaticAdjudication('audit',3), normal
moves e2e4,d7d5,f1b5+. Core: ONGOING. Old Native: MAX_PLY. Core c7c6 succeeds;
old semantic_make_checked rejects it. This is a pre-existing lower-level error,
not proof that deleting duplicate Core PV traversal introduced the mismatch.
The earlier caller-only Dot review explicitly did not establish full C equivalence.

Shared automatic-status code now serves terminal adjudication and the checked
transition's rule-ply gate. PENDING remains ONGOING after the rule limit, while
mate/stalemate/repetition precedence stays. c7c6 continues; b5a4 stops the
threshold actor's checking continuation and yields NO_CONTEST. Root imports
permit full current state/history beyond the RULE limit, bounded by actual
GC_SEM_MAX_PLY1024 storage. Board/hand/aux/fullSHA and actor/check history are
compared against a newly imported public child after every test move.

No history tail is truncated. Full append/guarded enumeration at capacity and
requests whose declared search path plus availability headroom cannot fit raise
explicit NotImplementedError directing callers to existing Core execution/search.
The check is conservative; it does not assert every rejected request would
actually exhaust storage. Native-only APIs do not silently change evaluator,
algorithm, result schema or claim a completed search. Core AlphaBeta/provider
fallback remains available and tested on the same PENDING game. This is a fixed
implementation capacity, not MAX_PLY/repetition/stalemate or an empty legal set.
The1024-ply boundary fixture is a transport test, not a reachable-game claim.

A semantic_pending_continuation capability marks the repaired image. Automatic
terminal/search authority and public checked moves reject older images with a
clear rebuild/Core instruction; creating-backend ownership remains. Rebuild the
Native extension when installing this source. Existing defaults/UI are unchanged.

The existing pending caller patch is retained after this underlying repair:
one checked Native PV traversal/leaf state replaces duplicated discarded Core
traversal; terminal-before-next-decision and final canonical declaration guards,
public action identity and IllegalActionError remain. All79 result fields and
legacy imports/aliases remain. Qualification tests keep independent Core replay;
production no longer duplicates it per call. This is not a universal equivalence
proof, caller-authority change is explicit, and local exposed cost savings are
not general strength/speed gains. Earlier research batches remain frozen and
queued separately, not rerun or claimed independently validated by Dot.

## Disposition and ownership

|Advice/source|Decision and concrete closure|
|---|---|
|Dot1792050152: PENDING/max_ply, next checked edge|Adopt: actual witness reproduced, shared authority/import/capacity tests and final rebuilt regression.|
|CHAT_Comments1792050030: duplicated PV work|Already in progress: deliver existing caller only with the underlying repair; no second project/framework.|
|Same comment: result/diagnostics coupling|Inventory confirms coupling; defer new API until an actual consumer migration needs it. Preserve79 fields/defaults.|
|Same comment: many AUX experiment scripts|Use existing AUX runner; retain frozen entries/source snapshots. No bulk merge/deletion based on file count.|
|CHAT_Comments1792050050: policy/direction mixing|Adopt minimal separation: AGENTS durable authority/constraints, mainline revisable route/reasons, manual operating commands; historic details recoverable at fixed Git.|
|Same comment: wrong inherited AUX branch|AUX fixed its own DEV_AUX/sidemission entry; PRIMARY reads fixed source, does not edit checkout.|
|Dot1792050257: cursor cancel/deadline gap|AUX added post-terminal and post-cursor polls; real verified cursor injection tests; fixed source reviewed by PRIMARY.|
|Same supplement: C-to-D/interaction missing|AUX added already-paid fixed-opponent factorial report, 0new games/go or retraining; PRIMARY checked published arithmetic and all family/unknown fields.|
|Old non-replay false-PV concern|Already scoped and real-rule regression retained; no unrestricted main-order change or new research batch.|
|Old PRIVATE plan|Superseded; PUBLIC for direct Dot/Chat access, change only on NEW user direction.|

The two CHAT_Comments and primary/AUX supplement threads were fully read; all
reported no additional pages. Exact account-bearing originals are saved privately
before reconcile; this report contains project technical conclusions only.
PRIMARY consulted/recorded the new supplement, not only the old COMPLETED status.

## Native consumer and transition inventory

Actual consumer: learning.selfplay.collect_self_play -> SemanticSearchEngine.search
-> owned semantic_engine_search -> public result -> session.submit. Per move root
packing transports all board/hands/aux/relevant history; C performs the search
transitions, and the caller performs one checked Native edge per physical PV move
for validated leaf features. Self-play additionally replays that PV through Core
because it consumes the actual Core leaf position/key/material training features;
this replay is used, not the discarded duplicate removed from the caller.

Self-play directly needs action/declaration/PV/completed_depth/dynamic_features;
arena additionally records score/nodes/selective_depth/kernel time/termination/
fallback and opt-in ordering/trace metadata. A result object has79 fields; this is
real coupling, not measured proof that a new diagnostics object saves runtime or
maintenance. No new nested results, opt-in switch, serializer or public schema
is introduced here. Frozen checkpoint/rules/limits/profiles and existing arena/
trajectory serializers remain the actual configuration/output boundaries.

AUX's actual inspected entry is generic_proof_scaled_study run FOLDER -> shared
native study -> SizedNativeDriver -> RoyalActor/full public state ->
ProofMaterialPlayer -> bounded prover/independent verifier/cursor or remaining-
budget modified material-only Fairy callback. Physical moves are publicly applied
and observed by both cursors. FEN is a scoped board bridge, not complete generic
history; public Core owns actual history/terminal. Exact dimensions, budgets,
prices, roles, H/tail and source identities remain in existing frozen plan/output.
The owner documents actual dependencies and conversions at fixed11dddd80 below;
this inventory does not claim PRIMARY executed AUX experiments.

## Auxiliary fixed delivery and paired arithmetic

Reviewed fixed sidemission11dddd801c68ef9289ff8293dba1dbb00701ede9:
[entry/closure](https://github.com/WD-nanophotonics/GenericChess/blob/11dddd801c68ef9289ff8293dba1dbb00701ede9/docs/research/DEV_AUX_ENTRY_CONTRACT.md),
[player](https://github.com/WD-nanophotonics/GenericChess/blob/11dddd801c68ef9289ff8293dba1dbb00701ede9/scripts/generic_proof_player.py),
[actual cursor test](https://github.com/WD-nanophotonics/GenericChess/blob/11dddd801c68ef9289ff8293dba1dbb00701ede9/tests/development/test_generic_proof_player.py),
[factorial report](https://github.com/WD-nanophotonics/GenericChess/blob/11dddd801c68ef9289ff8293dba1dbb00701ede9/results/dev_aux/task1806/factorial_report.json).

AUX reports32focused passes and complete remoteSHA verification. PRIMARY read
source/test/report and independently checked published cell/vector arithmetic,
not those tests or raw games; no merge, worker or cross-checkout mutation.

1797 C/D both net10/64: two more wins AND two more losses. C-to-D0, interaction0;
8family paired intervals[0,0], not population equivalence. Actual game seconds
30.440679->54.943160. 1798 Cnet8/64->Dnet10/64: two UNKNOWN->WIN, delta+.03125,
interaction+.03125, family95[0,.09375], from one of8families; seconds
26.791882->43.912238. All planned64slots/cell and missing0 retained, role/opponent
strata and W/L/draw/UNKNOWN transitions stay explicit. No confirmed general
solver benefit or causal claim from baseline-only null; old1791/1792 change both
players and are excluded from isolated interaction. Bootstrap CI is an exposed
exploratory owner analysis, not a PRIMARY reproduction or confirmatory test.

AUX's previously authorized512-game horizon batch had already begun before the
later repair-first coordination; it completed within original caps and is separate
from this zero-new-game correction. Preserve that ordering, not a retroactive
claim no research ran concurrently. No further batch is needed for this repair.

## Recovery scenario check and applicability

|Scenario|Authority, applicability and outcome|
|---|---|
|Old PRIVATE permission reappears after compact|User2026-10-15 current decision/reason, both Agents: stay PUBLIC; old grant superseded, not a retry.|
|Small WDL/solver control could change a decision|Continuing small-work permission + current mainline: allowed in owner lane; repair first now, later selection revisable. No exact-WDL admission prerequisite.|
|Repeat a negative search optimization unchanged|Frozen integrity/current evidence: preserve result, do not rerun unchanged; choose changed premise/decision-changing question.|
|AUX copied primary entry|User-established ownership: DEV_AUX/sidemission only, PRIMARY/sandbox only; actual fixed AUX entry now agrees.|

Standing permissions/stops/PII/Agent and fair-comparison boundaries remain durable
until explicit user change.60–90minute research segments and>1hour single-run
consultation are user requirements, not expired experimental cost thresholds;
the cleanup preserves them. Current route priorities are revisable mainline
selection, not a permanent prohibition. Historical manual/priority prose remains
at4f6858b1, no new index/config/approval layer. Operational entry line counts
fall from AGENTS400/manual~522/mainline202 to199/148/93; reduced text is not a
claim of measured future model compliance. Actual new user direction always wins.

## Verification and limits

Test counts, rebuilt source hashes and final qualification are recorded in
[data/slack_review_fixes_20261015.json](data/slack_review_fixes_20261015.json).
First rebuilt full suite2647 passes; after adding old-image capability/Core-path
coverage, final51focused passes, final full2648passes (0failures/errors/skips). Source-only package export
rebuilt C without copying a pyd and passed35related tests; initial8 missing
helper imports were corrected with exact existing test/script source, no product
change. An oversize Native search request explicitly declined and the existing
Core AlphaBeta path returned a legal action on the same unmodified PENDING root.
Initial old image had4failures/3passes on7new tests. Build initially could not
read the Python import library under sandbox; normal supported escalation
succeeded. A Flat test evaluator initially omitted capture_order_value; fixing
that fixture restored the final focused checks. Failed setup evidence is retained
privately. An initial default-codepage documentation read failed; explicit UTF-8
and the exact historical Git body restored text before publication. No SAC cause, security-setting change or user intervention is claimed.
No product UI/default, learned prices, frozen batch caps or auxiliary source was
modified by PRIMARY. No whole-domain equivalence, strength or new performance
claim follows from this bounded defect closure.
