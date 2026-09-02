# ADR-117: F47 endpoint-density composite diagnosis

- Status: Diagnosis-only F47 prototype
- Baseline: `979c7e026442e9dbb479658d0a770daefd15da85`
- H47A: standalone endpoint-completion protocol checkpoint
- Audit: `scripts/audit_f47_endpoint_density_composite.py`
- Production change: none; F48 was not executed

## Decision

F47 adds one parameter-free endpoint completion to the accepted ordinary,
deduplicated semantic candidate population. For each owner/source/density and
canonical candidate relation, `attack_only = target_enemy AND NOT target_empty`.
For attack-only candidates only, the accepted `clear * density / 2` contribution
receives the missing split-control mass `clear * (1 - density / 2)`, where
`clear = (1-density) ** path_length`. The completed attack-only contribution is
therefore exactly `clear`. Quiet-only and dual-use quiet+attack candidates are
unchanged, and relation multiplicity on one target is not rewarded twice.

The audit freezes five variants: current D46-0 arithmetic control, endpoint
arithmetic, endpoint geometric, endpoint harmonic, and endpoint lower envelope.
All use the existing five density points and weights, existing raw-capability
weights, existing median/round/anchor/clamp normalization, and existing hand
relation. No endpoint coefficient, fitted probability, new density point,
conditional feature, or production evaluator path is introduced.

## Controls and no-drift evidence

Synthetic controls pass same-target no-double-count, split-target positive-gap,
no-attack zero-gap, dual-use-only zero-gap, conditional-pattern exclusion,
owner mirror, type/ruleset rename, action ordering, and generated geometry-ID
invariance. The Western Pawn has a derived nonzero attack-only gap. The
Standard-Shogi Pawn gap is reported from compiled semantics rather than
assumed; it is zero in the accepted ruleset.

For every variant and both rulesets, the audit derives per-type candidate
population equality, coverage/reachability/path-efficiency equality,
endpoint-definition equality except the explicit attack-only completion,
normalization equality with the accepted F42 helper, unchanged hand relation,
unchanged graph-global weights, unchanged density points/weights, and no
conditional capability inclusion. D46-0 reproduces every F42/F46 curve,
reduced mobility, raw capability, and normalized board value per type in both
rulesets.

## Result

C47-1, C47-2, and C47-3 pass structural, semantic, no-drift, and Standard-Shogi
gates. Each strictly improves interval distance for every Western N/B/R/Q raw
ratio, but none passes all frozen Western bands. C47-4 improves three pieces
but moves the Q ratio farther from its band, so it is a directional mismatch.
No variant qualifies. The executable selector returns:

`ENDPOINT_DENSITY_COMPOSITE_INSUFFICIENT`
→ `F48_GENERIC_MATERIAL_PRIOR_REASSESSMENT`

The cross-stage diagnosis is that endpoint completion recovers substantial
Western Pawn suppression from attack-only geometry and brings the ratios toward
their intervals, while density reduction then overcompresses the absolute
material scale. The two mechanisms therefore provide complementary structural
information but do not, in this parameter-free scalar construction, recover
the full Western material bands. Standard Shogi retains the frozen positive
control under cosine, Spearman, pairwise ordering, rank displacement, and
hand/board gates.

F47 remains audit-only. F48, production integration, AlphaSho/search/self-play,
training, F43 combination, and master promotion remain out of scope.
