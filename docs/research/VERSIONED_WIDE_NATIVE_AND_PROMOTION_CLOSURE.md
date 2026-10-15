# Versioned wide Native execution and promotion closure

Science remains **OPEN**. This segment repairs two observed implementation
problems and qualifies a private wide-board execution prototype. It does not
activate a new product backend, establish playing strength or close the complete
generated-rule domain. Summary: data/versioned_wide_native_20261015.json;
source, declarations, raw technical results and failed attempts:
../archive/versioned_wide_native_20261015/evidence.zip with member manifest.

## Product changes

The semantic Native representation accidentally inherited the legacy maximum of
8 promotion targets while supporting64 types. Fresh24-board input exposed it;
an ordinary8-board reproduction also failed. Four predeclared regressions cover
9/62 targets and optional/forced promotion. All four failed the old compiler with
`too many promotion targets`. Semantic arrays/parser/runtime/candidate storage now
use the64-type bound; the legacy8 limit remains separate. Tests exercise type63,
all legal actions, checked child state/key/history. This fix was already delivered
at ca1431724af30346873dcfa3ffd119a8563e955a with full2563 and focused62 tests.
Rebuild the Native extension; old binaries retain the old rejection.

Generation on larger boards wasted compilation and promotion/drop-mask work on
candidates whose initial anchors were already attacked. The generator now draws
the same initial setup before deterministic mask derivation and rejects those
candidates with the existing atom geometry and occupied-ray blocking semantics.
Pinned pieces attack; rays protect their first occupied square. This is exact for
this atom-only generator, not a replacement validator for arbitrary semantic DSL.
Survivors still pass the original complete compiler, hard checks and soft filters.
No RNG draws, accepted-rule semantics or configured opening filters are removed.

Eight declared seeds3501..3508, sizes16/18/24/32 twice and16attempts per arm,
compare original versus early rejection in alternating order. Seven accepted
serialized rule hashes match exactly; one pair exhausts16attempts. All attempt
counts and final RNG-state hashes match. Baseline79.8145s versus41.7142s;
these are paired incremental process costs with shared cache warmth/concurrent
load, not cold-process or universal speed guarantees. Twelve regressions include
the eight baseline rule records and64 typed occupancy cases at each of4/8/18/32,
checked against Core attacks with both positive/negative outcomes. The final
actual full suite passes **2575** tests in295.560s; exact collected-node hash is
in the summary/archive. No code changed after that full run.

A separate documentation correction restores five dash sequences corrupted by
an omitted UTF-8 read in the previous handoff publication. Original defect and
correction evidence remain; no semantic source or result was affected.

## Private versioned interface

The product V1 action/payload, board<=16 admission, defaults and fallback remain.
The private candidate uses payload5, distinct capsules and a63-bit dense action:
to10/from10/promotion7/base6/kind4/pattern8/geometry12/current-actor6. Bit63 stays
a declaration tag; no-promotion127 and drop-source1023 have explicit contexts.
Semantic capacity1024 is distinct from legacy256. This admits tested boards<=32;
it is a scoped implementation, not a redefinition of GenericChess generality.
A process-local private module substitution enabled experiments; global module
swapping is not the proposed production routing API.

Actual C tests include10150 boundary/random codec roundtrips,20000 cross-version
action rejects and6 payload/capsule isolation cases. Five constructed16/18/32
fixtures exercise target255/256/323/1023, actual promotion, capture-to-hand, reply,
drop, auxiliary state, complete history, WIN/NO_CONTEST declarations and bit63 WIN
search. Final64-target sources requalify the semantic cases and62 product guards.
Seventeen existing full roots match Core complete action sets and1301 checked
edges: board, hands, auxiliary state, side, ply, canonical key, exact SHA256
history and events. The supplied qualification-inputs.json and clean helper
replay all17/1301 while rejecting access to other private evidence folders.
This is an actual local dependency-audited replay, not a clean-machine install.

First conversion mistakenly changed an independent promotion-pair key shift16
to20 and missed50 promotions; the failed source/output is preserved and corrected.
Initial boundary/input preparation errors and a driver PV-validation API error
are also retained. The first search driver returned at least30 queries before
its result validation failed; exact interrupted in-flight work is unknown. Those
costs are not silently counted as successful planned queries or free work.

## Capacity, policy and cost attribution

PhaseA retained the old8-target semantic arrays. Its272 slots contain240 actual
calls and32 capacity declines. Controlled private V2cap256 versus installed V1
has52 completed identical full-work pairs: kernel ratio1.0148, caller.9162.
Cap512/cap256 has52:1.0441/1.0140; cap1024/cap512 has64:1.0741/1.0185.
Position bytes53920/55968/60064 are structure sizes, not peak process memory.
These tiny-case concurrent measurements distinguish fixed capacity overhead from
codec feasibility; they are not a universal performance model. Exact36-source
phaseA hashes were recovered including original CRLF. Final phaseB64-target
sources are separate: phaseA timing is not relabeled as final-source timing.
The copied build-result file once mislabeled promo8 was renamed without changing
its bytes; evidence-label-corrections.json records the correction.

The68-query Core/wide qualifier originally counted only14 metadata-identical
pairs. That was overly restrictive: when requested q0 and both qnode counts are0,
Core's unused configured hard8 and Native0 do not imply different search policy.
The corrected same-policy comparison has31 score-equal pairs;3 retained different
objectives. A further34-call explicit hard0 control completes17D2 equal-score
pairs. Eight checked FEN probes refute the initial inference of default q0 check
extensions. Product Core metadata convention remains unchanged. This exemption
must NOT be applied to requested q4 searches whose reserve has fallen to ordinary0:
checked q extensions can still run. Initial mistaken scope statements are kept.

All four prior binary-q resource depth losses are classified, with8 same-root
controls and no rerun/cap extension: two3003/4s orderings retainD1/q0 after time
instead of plainD2/q4, paying about3.02M rather than1.93M candidate work; two3005/16s
orderings hit hard8 around5.63s and retainD8 versus plainD9. Counts include unfinished
iterations and outer q work, not unique physical states. They do not prove strength
loss or license an artificial q1 downgrade.

## Fresh full-rule transfer, phaseB

Seeds3301..3312 and16/18/24/32 sizes were declared before queries, roots at ply0/8.
Three32-board families are preparation-censored:3304's original default1000attempt
preparer was interrupted after observed84.45CPU seconds/426MB working set;
3308/3312 then hit explicit45s preparation caps. These are not query caps or exact
final total costs. No replacement seeds were selected. Nine families/18 roots
remain, with6 originally planned32 snapshots absent. The early generator
optimization above uses different seeds, not a retrospective rescue of these.

PhaseA exposed the promotion capacity rejection after17 returned queries and one
zero-query compilation rejection. After repair phaseB reuses the SAME inputs and
5s fixedD2 plus2/16s maxD12 budgets. It is exposed development, not an untouched
validation claim. Flat leaves K0/other types100 retain board-current/hand-base
semantics; TT0/main ordering off and q4/hard8 are held. Current Core uses existing
Native consumers where supported and actual fallback otherwise:36 provider and72
fallback records, rather than a fictional pure-Python baseline.

The216 calls close in1656.985 producer seconds, below the declared2700s fuse.
The72 equal-budget resource pairs have23 deeper retained results,49 equal and0
shallower.44 choose the same action and56 retain the same actual q depth.
Across modes,73 pairs with matching retained depth/q/hard policy all have equal
scores after explicit mate-unit normalization. Six closed fixedD2/q4 pairs have
kernel/caller geometric ratios.1420/.1985; these are only3 roots on16/18 boards,
with NO closed24 CoreD2 pair. Different algorithms/scheduling/order/work and
concurrent load preclude interpreting this as a pure backend speed factor.
Maximum caller-minus-search-budget1.593s shows query caps are not end-to-end caps.
All216 selected actions/PVs are Core-legal and roots retain exact state/history.
A separate final full-root check verifies all2963 actions across18 roots (maximum
10 promotion targets), payload reconstruction, keys, history and auxiliary state.
Eight24-board TT context pairs have7 matching objectives with equal scores and
one censored/different objective. Four pre/during cancellation calls actually
cancel, and all four same-engine reuse q0D2 calls complete. Timer callbacks join.
No producer remains running. The TT plan's rough72s estimate understated the
sum of fixed call upper bounds84s; no individual call budget was extended.

These are completion/cost and semantic preservation results, not WDL/strength
improvement. Old preparation censors, driver failures, mismatched policies,
negative q results and imperfect timing all remain in the evidence.

## Collaboration and next decision

DEV_AUX fixed51 report8ac8a9fc44354cc84ff5fbfe5e3361cb844be050 was read;
its27 vectors have729 pair order/tie relations unchanged independently checked.
Primary did not reproduce its raw games. The complete new52 thread and fixed
report e4634d72a6499f43a607ba475c055af53b7c4e46 were also read. Positive small-board
policy WDL, inconsistent TRAIN prices, unresolved promotion interaction and failed
strong-opponent/board transfer support continuing scoped auxiliary learning,
not changing primary prices or declaring human-price recovery. Dot's52 advice
used51 evidence; it was not independent execution of52 or this wide prototype.
See ../operations/COLLABORATION_LOG.md for roles, decisions and actual limits.

Select one next mainline task: bind backend/capability information per ruleset
and qualify explicit V1/V2 coexistence plus unsupported fallback before product
activation. A global mutable module switch is inadequate. The positive private
completion curve justifies this small interface step; it does not justify raising
production guards alone. Backup is new predeclared32-rule full-mechanism evidence
using the now-cheaper generator, preserving old censors. Price learning remains
in its independent auxiliary lane. No extra worker, fees or UI writes occurred.
