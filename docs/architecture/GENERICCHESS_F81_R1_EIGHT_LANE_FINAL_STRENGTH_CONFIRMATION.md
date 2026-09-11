# GenericChess F81-R1: eight-lane fresh-corpus final strength confirmation

Status: `PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMED`.

The F81-R1 work order completed the same frozen final confirmation with eight
game lanes. The execution-only change did not retrain, mutate the candidate,
or change production evaluator, search, Arena, or corpus semantics.

## Frozen inputs

The work-order baseline was
`ef9a165ddebc8206e61327c196dc0baec2b9bd75`; the execution harness was
published at `50a68fa734c890466769b0876c26b0f1d8314fe8`.

The fixed identities were parent
`d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`, child
`f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`, and
candidate model
`b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6`.

The evaluator-neutral Standard-Shogi corpus remained the previously frozen
seed-`810501` corpus at
`artifacts/f81_final_confirmation/openings.json`, corpus ID
`67b9dafc51a618645c3328228c30a8744cc8f988395a7d54d382b65276dc935c`. It has
eight unique final positions and zero overlap with F62, F75, F77, and F78.
No `generate_arena_openings()` call was made by the R1 execution harness.

## Arena execution

The stage ran eight pairs / sixteen games with swapped owners, fresh engines
per game, 512 parent and child nodes per move, depth 12, 8 MiB TT, telemetry
capture, product root-window pruning, and no early stopping. The execution
caps were 3,600 seconds per game and stage, 262,144 nodes per game, 512 plies
per game, and 16 maximum stage games. Effective game lanes were exactly 8.

All 16 games and 8 pairs completed. The resumability replay returned
`COMPLETE` with identical status, counts, and summary. Contract failures were
empty; all telemetry rows had root-window pruning enabled, no pruning field
was missing, and the maximum observed search node count was 512.

## Fresh-corpus result

Fresh pair scores were `[1.0, 0.5, 0.5, 0.0, 0.5, 0.75, 1.0, 0.75]`. The mean
pair score was `0.625`; child-better/tied/worse pairs were `4/3/1`; the
bootstrap diagnostic interval was `[0.40625, 0.8125]`; and game W/D/L was
`9/2/5`.

By the unchanged final gate (complete eight pairs, mean greater than `0.5`,
and child-better pairs greater than child-worse pairs), the fresh corpus
confirms the candidate:

`PARENT_ANCHORED_FULL_RESIDUAL_FINAL_CONFIRMED`

The durable summary evidence is
`artifacts/f81_final_confirmation/final_strength_evidence.json`; its content
SHA-256 is
`dc769e52c7d5d6357fabfb640c88a51ab3b0600b9c97aec8919c810b7d25e938`. Raw
game progress and detailed per-search rows remain in the ignored runtime
namespace `.generic_chess_flow/f81-r1-eight-lane-final-confirmation`.

`champion_before` is the fixed parent checkpoint and `champion_after` is the
fixed child checkpoint. Promotion of `master` remains HOLD; this confirmation
does not start another generation or authorize promotion.
