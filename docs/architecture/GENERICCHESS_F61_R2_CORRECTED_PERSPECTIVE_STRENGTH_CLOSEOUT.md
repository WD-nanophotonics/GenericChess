# F61 R2 corrected-perspective fresh-strength closeout

Status: verified evidence; no promotion performed.

## Provenance

- Work order: `GENERICCHESS-F61-CORRECTIVE-R2-PERSPECTIVE-CERTIFICATION-AND-FRESH-STRENGTH`
- Heavy run: `f61-r2-corrected-7921245e0d19` (completed normally, exit 0)
- Raw result (excluded from Git): `.generic_chess_flow/f61-strength-first-triage/f61_r2_results.json`
- Raw result SHA-256: `F17AAF568861FE92723006BE814B301A619279E530230D83493BC86B8D5B1C9D`
- Parent checkpoint: `2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362`
- Corrected training binding: `f61-corrected-perspective`

## Result

The selected candidate is `F60_D0_PAIRWISE_SEED_59012`, corrected checkpoint
`d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`.
Its fresh 32-pair confirmation produced 40 wins, 22 losses, and 2 draws at
game level, for a score rate and mean pair score of `0.640625`; the pair-level
bootstrap 95% interval was `[0.5234375, 0.7578125]`.

Screening and extension results were:

| Candidate | Corrected checkpoint | Search changes | 4-pair score (95% CI) | 8-pair score (95% CI) | 32-pair score (95% CI) |
| --- | --- | ---: | ---: | ---: | ---: |
| `F60_D0_PAIRWISE_SEED_59012` | `d0e6a024...ae43362` | 8/8 | 0.6875 [0.375, 1.0] | 0.65625 [0.4375, 0.875] | 0.640625 [0.5234375, 0.7578125] |
| `F60_D12_MEDIAN_DEVELOPMENT_SEED` | `da51634c...a32946d3` | 8/8 | 0.4375 [0.25, 0.625] | — | — |
| `F60_D2_MEDIAN_DEVELOPMENT_SEED` | `3bc950ed...e1825f29` | 7/8 | 0.6875 [0.25, 1.0] | — | — |

## Integrity checks

- All five persisted Arena stages were loaded through the resumable Arena
  identity contract and semantically replayed from their openings to their
  recorded final positions: 52 complete color-swapped pairs / 104 games.
- Recomputed pair scores, game aggregates, bootstrap intervals, actions,
  results, and final-position identities matched the raw result exactly.
- The D0 4/8/32 stages used 44 distinct openings across 44 pairs; the 32-pair
  confirmation used 32/32 distinct openings.
- Each progress manifest binds the ruleset fingerprint, full parent and child
  checkpoint IDs, every Arena configuration field, and ordered opening content.
- The established resilience, identity, perspective, Arena-integrity, and flow
  regression suite passed: 78 tests.

## Durable conclusion

Under the corrected perspective binding and fresh-opening protocol, the D0
candidate's 32-pair confirmation interval remains above 0.5. This closes the
requested strength evidence only; it does not authorize or perform a master
promotion.
