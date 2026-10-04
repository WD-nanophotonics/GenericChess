# Typed capture-incidence results, 2026-10-04

Frozen protocol TYPED_CAPTURE_KERNEL_PROTOCOL.md SHA256
ce48349d480ba49b669f0949e6cd258a4d4dc60994654ae4cb2112433fed293b.
Runner audit_typed_capture_kernel.py; complete raw accounting and source hashes
are in data/typed_capture_kernel_20261004.json. First real-game run completed
in0.344 seconds, zero state transitions, within10 seconds/100k candidates per
type. Eleven focused incidence/composer tests passed before observation.

| Scope | All-square rank | Active-support rank | Identical active victim columns |
| --- | --- | --- | --- |
| Chess | 1 | 2 | B/N/Q/R; P separate |
| Standard Shogi | 1 | 3 | B/G/R/S; L/P; N separate |

First exact nonzero minors: Chess rowsB,N/columnsB,P determinant19/63504;
Shogi rowsB,G/columnsB,L determinant199/777600. Thus the changed placement
assumption introduces typed information in both games. It does not merely
rename a rank1 untyped matrix. The information is limited: types with identical
victim supports still have identical columns. Distinct columns are not evidence
of opponent choice, positional importance or useful material values.

Active support sizes: Chess P56 per owner, all other initial ordinary types64;
Shogi P/L72, N63, B/G/R/S81. In particular Chess P56 is NOT the actual-inventory
sampler's48-square legal-history structural support. The compiled intrinsic
actions allow a hypothetical first-rank Pawn; this diagnostic intentionally
uses activity, not certified reachability. No piece-name exceptions were used
to repair that discrepancy. Shogi empty-board activity is likewise not a
complete legal-context predicate. Two-token boards lack anchors and are not
passed to the full legal game executor.

All-square controls had identical columns exactly. The test oracle explicitly
enumerates distinct pair populations independently of the counting formula;
it also checks owner/square mirroring, type-label ordering, promotion-branch
deduplication, blocked-path refutation and off-target removal. Unsupported
semantics/multiple victims/empty pair populations fail closed.

## Mainline decision and next construction question

Reject independent victim-type weighting as a new relative-value principle;
retain typed placement as a distinct exploratory input. No eigenvector,
recurrence, hand premium or material vector has been produced. Its rank result
does not select positive versus negative feedback or a discount parameter.

A finite alternative to unexplained infinite feedback is *counterfactual
threat denial*: capturing j removes j's future ability to capture one's own
resources. A two-edge motif i->j->k could measure that structural capacity
without calling it an executed sequence: j cannot act after being removed.
Multiplying mean incidence matrices would also assume away the shared-square,
occupancy and victim-selection dependencies. Next decide whether a joint
counterfactual motif has a coherent declared context and a cheap falsifier,
rather than computing a spectral vector first and explaining it afterwards.
Keep construction and separate leaf-decision deployment evidence distinct.
