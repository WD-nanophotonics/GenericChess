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

## Corrective R1 closure

The first-pass H47A provenance defect is retained as history and is not
rewritten. Standalone H47R1A (`tests/fixtures/f47r1_endpoint_density_composite_manifest.json`)
binds the accepted F44 endpoint, F45 placement, and F46 density authorities by
path and SHA-256, and is verified before the F47 audit runs. It is anchored to
the immediate F47 candidate `d8d39bb4ef15f018e97afedf97733041490686b2` and has
no observed result field.

R1 replaces nominal structural checks with executable perturbations: the F47
candidate fingerprint contains owner/source, target, path, relation set, and
canonical geometry/channel identity; it is compared independently with the
accepted F44 extraction and the F41 core candidate helper. Duplicate semantic
descriptions, actual X→Y type relabeling, RuleSet metadata relabeling, reversed
action order, and insertion of an unrelated action that shifts generated
geometry IDs all preserve the fingerprint and gap curve. A known ray-path
control mechanically verifies `clear * (1 - density / 2)`. C47-0 reproduces
F46/F42 curves, reductions, raw values, and normalized values, while C47-1
through C47-4 directly reproduce their frozen F46 reducer definitions.

The complete semantic predicate now includes Western-Pawn nonzero gap,
compiled Standard-Shogi-Pawn derivation, and relation-multiplicity control.
The selector reachability evidence also executes the mixed case in which a
coherent insufficiency and directional mismatch coexist; coherent
insufficiency wins by the frozen selector priority. These corrections do not
change the evidence-derived classification: `ENDPOINT_DENSITY_COMPOSITE_INSUFFICIENT`
→ `F48_GENERIC_MATERIAL_PRIOR_REASSESSMENT`. F48 remains out of scope.

## Corrective R4R1 legacy-hash migration closure

R3 established that the F42-F44 historical `sha256` fields were captured from
checkout bytes and therefore have legacy CRLF, LF, mixed, or nonreproducible
semantics. Their values remain unchanged in the original frozen manifests.
Standalone H47R4A (`73b5e5f7f97b4e78aa4dcd6331698c7e61398519`) freezes
`tests/fixtures/f47r4_legacy_provenance_migration.json`, a complete 34-row
ledger covering F42-F45 repository bindings and the direct H47R1A F44/F45/F46
authority bindings. Each row preserves `legacy_sha256` and its explicit
semantics while separately freezing `canonical_ref`, `canonical_path`, and
`repository_blob_sha256`.

The non-production `scripts/repository_provenance.py` helper retrieves raw
bytes only through `git cat-file blob <ref>:<path>`. It exposes raw retrieval,
canonical SHA-256 calculation, structured expected-hash comparison, missing
ref/path errors, and explicit legacy-ledger validation. No checkout bytes are
used for canonical provenance, no newline normalization is performed, and no
worktree is mutated. F45 generated `.generic_chess_flow` evidence remains a
working-tree-local artifact and is not reinterpreted as repository authority.

Negative tests cover altered canonical hashes, paths, refs, and missing blobs.
The Windows semantic test proves on a pristine `core.autocrlf=true` checkout
that a CRLF working-tree digest can differ while the raw Git-blob digest and
canonical binding remain stable. No manifest, fixture, `.gitattributes`,
production, evaluator, search, or allowlist content was changed.
