# GenericChess F86I reversible ordinary-mobility rescue candidate

Status: bounded experimental candidate evaluation. This checkpoint evaluates
one preregistered candidate profile and does not modify the production/default
generator. The manifest was published first in prep checkpoint
`af69b4258d4a45fbab07c8de516a586543bccdf7`; the result artifacts and this
report are the subsequent result checkpoint. The immutable result SHA and
report SHA are recorded by the Courier closeout for this checkpoint.

## Contract and authority

The candidate profile is
`ORTHO4_PLUS_REVERSE_CLOSED_ORDINARY`. The Anchor uses exactly the ORTHO4
offsets `(1,0),(-1,0),(0,1),(0,-1)`. Every ordinary movement atom has its exact
reverse counterpart: a LEAP reverses its offset, and a RAY reverses its
direction while preserving `max_steps`. Atoms are deduplicated and ordered
deterministically. There are no FULL8 moves, promotion, drops, HOME rules,
special rules, manual piece redesign, or production-generator changes.

The new artifacts use the corrected nested binding contract
`ruleset_fingerprints[sample_id][cell]`, with `cell = CANDIDATE`. The manifest
is the sole result authority; the runner loads candidate rulesets and tapes
from that published manifest and forbids result-driven replacement.

| sample | board / source seed | source fingerprint | candidate fingerprint | tape A / B |
|---|---:|---|---|---:|
| V4-2 | 4 / 861401 | `1b8547501a45ebc1344f7134319ed215de09a51dfb001270dc127e77528698ac` | `86581cc73bc9c2146eb5117384be4a717fa3bd8a87c2e123c6470434bbe47b01` | 8614011 / 8614012 |
| V4-3 | 4 / 861402 | `7e2ff9e15c2a0d1be5faa8c6697f22e488976a2d2ae9f077b85c6e71f95ff400` | `8ca58376a52e539c7c8519e902b8dd9e6991b002586d36d846a7a864fffea05d` | 8624301 / 8624302 |
| V4-4 | 4 / 861403 | `864e9aaf0f36b0a94024454a357e6787b3edd9cfd81898d1bea76dfc591b08d0` | `ed6784e034a0bd625be4d69bace6a459c9d16d590abf93066025115603ed0fde` | 8614031 / 8614032 |
| V4-5 | 4 / 861404 | `9a5f3de7a492fa4fa01ca1b4c2e7a11b24403cde87b79761b26e212d13221f24` | `effc9905d3b3afd3d67d4696ec0c259531f05feb380479f590179fb9fac063b1` | 8614041 / 8614042 |
| V5-2 | 5 / 861501 | `ddacec0f6b6fbffeb9135fbbbb658093d92ce0e5bce28665a87022b702d815d6` | `07db1004324033ce66feee06e92afee03277f34d1d0f84246405591f45fe058b` | 8615011 / 8615012 |
| V5-3 | 5 / 861502 | `d6e47a6fe19ab20538a1ec9539597b5765d0211cb608b15c262613a86e635297` | `29390db6050d1ba482a393f7466608a6f19d0df9e6d4f7c3bd3a556f2d194fff` | 8625301 / 8625302 |
| V5-4 | 5 / 861503 | `580475d4c25b8d5bb9d796902d383ac673bd00c3565e4609d07443bcc338ad04` | `653eba1d8e6bb4de5d0cee911a9f12351e0a673320c6d9357660d13c7f68fed3` | 8615031 / 8615032 |
| V5-5 | 5 / 861504 | `c3fa844c61ea944f9fd11560f00878337389f427a59d84958c312e38d5494d31` | `7d230178849e05cedbe295e4c623217313402611983e751e31481c92c32397b6` | 8615041 / 8615042 |

## Static mechanism check

The empty-mobility graph was checked for ordinary sink fraction, direct
reverse-edge fraction, nontrivial-SCC fraction, and monotone-DAG status. The
candidate is structurally reversible in all eight frozen samples: direct
reverse-edge fraction is `1.0`, every graph has a nontrivial SCC, and no graph
is a monotone DAG. Sink fractions reflect board-edge geometry rather than
irreversible ordinary movement.

| sample | ordinary sink fraction | direct reverse fraction | nontrivial SCC fraction | monotone DAG |
|---|---:|---:|---:|---|
| V4-2 | 0.000 | 1.000 | 1.000 | false |
| V4-3 | 0.000 | 1.000 | 1.000 | false |
| V4-4 | 0.125 | 1.000 | 0.875 | false |
| V4-5 | 0.125 | 1.000 | 0.875 | false |
| V5-2 | 0.080 | 1.000 | 0.920 | false |
| V5-3 | 0.000 | 1.000 | 1.000 | false |
| V5-4 | 0.000 | 1.000 | 1.000 | false |
| V5-5 | 0.040 | 1.000 | 0.960 | false |

## Static mate/template rescue check

The F86F static mate predicate was re-enumerated only for V4-3 and V5-3,
using the ordered caps of 2,048 candidate positions per cell and 4,096 total.
The candidate census is complete for V4-3 and cap-truncated for V5-3:

| sample | candidate checks | validated positions | templates | truncated | ordinary assignment | joint kinematic |
|---|---:|---:|---:|---|---:|---:|
| V4-3 | 504 | 398 | 40 | no | 0 | 0 |
| V5-3 | 2,048 | 1,890 | 98 | yes | 28 | 28 |

V4-3 routes to `REVERSIBILITY_RESCUE_INSUFFICIENT_KINEMATICALLY`: no
validated candidate template has a type-respecting ordinary assignment from
the opening, so no joint route exists. V5-3 is
`MATE_CAPACITY_UNRESOLVED_DUE_TO_CENSUS_CAP`; its 28 reachable templates and
optimistic lower bound of 10 plies are not a complete-census conclusion.
The same empty-board, occupancy-ignored analysis as F86H was used, so these
are necessary-condition results, not legal game paths.

## Dynamic smoke

The eight manifest-bound candidates were each played twice, A/B and B/A,
for exactly 16 real games, maximum 32 plies. Actions use canonical JSON action
ordering and the preregistered 32-value tapes with `floor(u * legal_count)`.
The raw game records are retained in `game_results.json`.

| terminal label | games |
|---|---:|
| checkmate | 1 |
| stalemate | 0 |
| repetition | 0 |
| ongoing@32 | 15 |

The one checkmate occurred in V5-5. The dynamic route is
`REVERSIBILITY_RESCUE_SHOWS_TERMINATION_VIABILITY`, but this is only a small
smoke signal: the 15 ongoing games are censored/unresolved and the result is
not benchmark admission or a claim of strength improvement.

No tactical probe nodes, BFS expansions, teacher/search compute, F85 compute,
Heavy job, or production generator change was used.

## Durable evidence and verification

- Manifest: `artifacts/f86i_reversibility_rescue/manifest.json`
- Static mechanism and census results: `artifacts/f86i_reversibility_rescue/static_results.json`
- Raw dynamic games: `artifacts/f86i_reversibility_rescue/game_results.json`
- Combined result and routing: `artifacts/f86i_reversibility_rescue/results.json`
- Runner: `scripts/f86i_reversibility_rescue.py`
- Contracts: `tests/test_f86i_reversibility_rescue_manifest.py` and
  `tests/test_f86i_reversibility_rescue.py`

Focused verification passed: 7 tests. The full bounded regression passed: 64
tests in 4.1 seconds.

Overall routing is therefore conservative and split by evidence:

```text
V4-3: REVERSIBILITY_RESCUE_INSUFFICIENT_KINEMATICALLY
V5-3: MATE_CAPACITY_UNRESOLVED_DUE_TO_CENSUS_CAP
dynamic smoke: REVERSIBILITY_RESCUE_SHOWS_TERMINATION_VIABILITY
```
