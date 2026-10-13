# Prefix-free static incoming schedule: bounded feasibility

The private representation changes static scheduling only. No production
compiler field, metadata cap, Native range, state/score/history cache, evaluator
policy or UI/default is changed. The only production delta this segment is the
coordinate allocation branch described in [cold input](COLD_RULE_COORDINATE.md).

## Observed capability boundary and changed premise

New complete generated20x20 rule1944 has178104 static capture endpoint rows.
The original65536 full-prefix row cap returns None; a separately frozen private
131072 cap attempt also returns None and executes zero searches. Both failures
remain. Raising that old cap again is not the selected experiment.
Native16 succeeds;20 has an explicit semantic board size out-of-range error,
and requested Native legality actually falls back to Core. This is an accelerator
boundary, not a restriction of the generic game domain. The full game still runs.
A first diagnostic used nonexistent support_report after successful16 compilation;
corrected report property and original error are retained, not miscalled Native
failure. Static geometry pruning speculation is rejected:95/145 pattern slots
on tested12/20 rules each contain exactly one compatible geometry.

The new premise stores only `(rank, pattern, gid, original_endpoint_index)` in
owner/target/source/current-type groups. It borrows existing immutable compiled
geometry paths and reconstructs the intermediate prefix only for a matching
actual actor. Rank preserves original pattern/type/source/gid/endpoint order.
The actual Piece still supplies base/current/owner to the unchanged binding and
path/state/slot guards. Leap prefixes are empty; ray prefix is `[:endpoint]`.
Endpoint indices are not renumbered after min_steps filtering. Every occurrence,
including different pattern/geometry references to an endpoint, stays.

One private build takes0.336s and retains178104 rows,42,710,286 bytes of recursive
Python structural sizes. Shared identities count once; borrowed dataclass payloads
are not descended. This is neither RSS nor an exact incremental/peak whole-heap
measurement. Prototype262144-row/64MiB structural limits are explicit. No persistent
position cache or new registry is involved. Whole fixed-node producer fuse500s.

## Semantic checks, consultation and current evidence

800 actual20-board target pairs plus full legalfrontier/entry cancellation agree.
Four actual4096-node q0 Core calls preserve every non-time decision/work/history/PV
field:30.842/31.736s old versus7.366/7.546s prototype,76.12/76.22% local savings.
Node work, search time and useful completed decisions remain separate evidence.

Dot's new AGENT_REQUEST root was sent once, raw fullreply saved, exact original
payload/account/root reconciled. It independently reads the fixed published IR/
executor, not the new private prototype or timings. Its decisive objection is
complete ordered row equality, beyond booleans. The actual178104 compressed rows
stream-equal the original geometry_candidates traversal, including multiplicity
and order; digest858b96ef73fe944b7eb804757416b13efff47caeb9d55dba5299158556db8c76.
No old enlarged full-prefix index is created for that reference check.

12 existing DSL fixtures through48 actual states cover cannon/castling/EP/nifu/
checking-drop, temporary slots, compound effects, postconditions, Chess/Shogi.
6472 target pairs (12944 actual queries), full legalfrontiers and all ordered
static rows agree. Nine helper synthetic cases add88 rows for leap/ray/drop,
min_steps and duplicate references. Internal repeated squares are deliberately
out-of-contract helper robustness: executable completeness rejects them. They
are not a production legal counterexample or full-domain proof.

Eight frozen16/64s calls on1944 keep all four complete retained result tuples
and D2/D3 depths; additional attempted work alone is not a horizon improvement.
32 fresh18/20-board1951–1954 q0/q4 calls preserve all non-time/work/PV/history
fields. Their256-node limit often retains D0/D1; do not pretend that is deep
completion evidence. A separate16-cell16/64s transfer on1952/1953 addresses
that uncertainty under the same public geometric evaluator and Core backend.

The16 actual fresh resource cells complete. On1952 (18-board), both16s pairs
complete D2→D3;64s staysD3. On1953 (20-board),16s staysD3; both64s pairs complete
D3→D4. Thus four ofeight paired cells are deeper, four unchanged, none shallower.
This is local useful completion evidence, not strength/WDL or a uniform leaf
horizon claim. All capped raw output/PVs/work and actual Core backend remain;
different completed depths are not scored as identical decisions. Fresh1951's
existing full-prefix index was available and low-node costs were nearly flat;
1952–1954 lacked it. This is a conditional fallback improvement, not universal
replacement speed or an automatically raised compilation cap.

## Decision and limits

The prefix-free schedule is selected for a bounded integration/memory comparison,
not immediate production admission from one20-board root. Full Native coverage
is still unsupported outside its range. Existing small-rule paths and callbacks,
all generated promotion/drop/aux/history semantics, original failures and fair
comparison conditions remain. No human-label fitting, holdout, learning, Elo,
other project/Agent writes or extra workers occur.

Zero-search namespace/inline-preparer faults were fixed immediately and kept.
The12:42 checkpoint prematurely called fresh resource running after a preparer
syntax failure; an explicit documentation correction preserves that mistake and
records the actual subsequent start. It is not counted as search or research.
The new ordered-row check is adopted; no authority is imported from peer advice.

[data index](data/cold_rule_coordinate_20261013.json) binds the explicit science
archive and member hashes. All raw Slack/account records and host XML stay private.
DEV_AUX remains in sidemission; its learning/horizon summaries are complementary,
not independently rerun or merged into this search acceptance.

Four actual static-size checks have begun the next choice. For1841/1843/1951,
old versus prefix-free structural sizes are1.78/1.45MB,6.47/5.24MB and23.27/17.53MB.
1953 old absent metadata is represented by72 bytes of None placeholders, NOT
zero full rule memory; the new schedule retains32.75MB. Small existing-index
query cost was nearly flat, so fallback-only integration remains a concrete
next comparison. These are structural proxies, not RSS/peak acceptance.
