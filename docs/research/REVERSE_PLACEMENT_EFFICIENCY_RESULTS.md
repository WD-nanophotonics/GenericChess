# Reverse placement: law correct, efficiency gate rejected

The frozen protocol and exact certificate are in
`REVERSE_PLACEMENT_EFFICIENCY_PROTOCOL.md` and
`data/reverse_placement_efficiency_20261004.json`. Counting actual compiled
Shogi masks gives W81=18,255,611,345,850 dead-free physical L/N layouts on the
empty board, versus U63=9,759,694,636,440 unrestricted layouts after Pawns.
The shared-normalizer proof therefore gives candidate/original raw acceptance
ratio 12049005724/22537791785, approximately 0.5346, for any identical subsequent
quiet/capture predicate. Expected raw attempts increase approximately 1.8705x.

Reverse placement with the compatible-Pawn acceptance weight preserves the
globally conditioned joint law; dropping that weight would not. It nevertheless
fails the predeclared raw-acceptance improvement gate. No sampler, corpus retry,
new labels or coefficients were produced. CPU performance of a full reverse
sampler was not measured. Exact counting, including compilation, took 0.109 s.
Tests reproduce the certificate, independently check the unrestricted integer
count and use an uneven toy compatibility graph to verify conditional law and
shared acceptance ratio, including a zero-support row and restricted predicate.

Continue with direct joint counting of each file's Pawn pair and L/N occupancy,
then truncated polynomial combination across files. That could remove intrinsic
rejection entirely while retaining the same global conditioning. Its counting,
uniform draw and preprocessing cost require independent verification before
another corpus protocol. The earlier corpus remains incomplete.
