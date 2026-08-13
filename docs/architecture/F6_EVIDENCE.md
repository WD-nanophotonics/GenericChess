# GenericChess F6 evidence

## 1. Status

`F6_RESULT = AUDIT_ONLY_PASS`

The target-directed geometry candidate was not promoted. It passed correctness
and provenance gates but failed the fixed usefulness threshold, so no H6B
production commit exists.

## 2. Baseline and provenance

The Gmail subject and complete attachment are preserved in
`inbox/2026-08-13_GenericChess-F6_Target-Directed_Semantic_Geometry_Check_Optimization.md`.

The locked F5 baseline was `b4372c077c2bce7bada05257a50e518807bf6f71`, with
master `4f1d03a308f5fd04a01bbd980c7411888ea1ed9d` and chat
`d6b0d5720efe23019a7a2b4cce72e05beee2e6c4`. H6A is `c5e5e3d` and was pushed
to `origin/sandbox`. The managed sandbox could not update `FETCH_HEAD`, but
the local origin refs matched the locked values before H6A and the push
completed without rewriting any ref.

## 3. Corpus and geometry equivalence

The certified Semantic Standard Shogi fingerprint is
`5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345`.
Four reachable nonterminal prefixes were queried at 162 attack queries each.
The geometry matrix covers compiled leap, ray, drop, owner-relative, edge,
corner, long-ray, and `min_steps` fixtures. Exact baseline/candidate tuples,
including canonical paths and ordering, produced zero mismatches.

## 4. Differential and legality parity

All certified attack/check comparisons passed. Full legal action order and S3
reply existence passed on the four prefixes and curated S4 fixtures covering
capture, drop-related attack contribution, own-anchor exposure, and
`squares_not_attacked`. No production semantic code was changed.

## 5. Diagnosis and performance gate

The baseline generated many unrelated geometry candidates after F5. The probe
avoided those tuple constructions, but still scanned the same compiled path.
The five-repetition 162-query aggregate was approximately 1x. Frozen search
results were:

```text
Profile A semantic aggregate: 809.196 ms -> 794.045 ms (+1.87%)
Profile B semantic aggregate: 3782.480 ms -> 3876.341 ms (-2.48%)
```

Parity held for action, score, PV, nodes, qnodes, completed depth, and
termination reason. The candidate therefore failed `LIKELY_USEFUL`; H6B was
not authorized and no production optimization was retained.

## 6. Validation and evidence

Full pytest passed. Fresh supported Zig build passed at 333312 bytes. The
closure directory contains the required diagnosis, parity, profile, cProfile,
gate, verdict, native-build, and SHA-256 manifest files.
