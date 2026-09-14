# F85 Native Calibrated TDLeaf Closeout

Date: 2026-09-15

## Scope

The F85 work order tested whether the default TDLeaf step was too small to
produce a measurable strength signal. It reused the F84 bounded native
self-play contract and the registered parent `c45623c0b905780ed1fd896a8f9364fd369bed1e641519f45fb40a3faf014d71` under the canonical standard shogi ruleset. No teacher labels, parameter sweep, second trajectory, or second applied update was allowed.

The implementation was published at sandbox commit
`e6adef5c4110c96b038df1355ccd37579b127b94` and tested with the F85, F84,
self-play, and TDLeaf suites.

## Stage A: calibrated update

The single trajectory used `games=1`, seed `840401`, 512 nodes per move,
depth 12, epsilon 0.10, 8 MiB TT, and a 64-ply bound. It ended as
`terminal=ongoing`, `truncated=true`, with 64 training points and finite
frozen-parent bootstrap `-0.6354471505664475`.

The nominal dry-run measured `weight_l2_delta=0.3539171520327391` with
`nominal_alpha=10.0`. The preregistered target was `0.10 * reference_median`
and the bounded result was `calibrated_alpha=2000.0` (the 200x upper clamp).
Exactly one applied update produced a changed successor with checkpoint
`21d26c88fe60e22ee90e334649361404f46f6fc9d6cbc7ad59a31eb689fcbf0a`,
64 positions, and `weight_l2_delta=70.80488150487201`.

Transient evidence hashes:

- Stage A envelope: `4c871ecb8600884738d0794206454a07447f692e3f784ea8499eaf73e6a93631`
- Stage A result: `a07ea236fcbce79f3360d7b9023adf7b357a36a7a8fab1d66e4b4ed45ad9220f`
- Candidate descriptor: `cf89caec9f6a9ec7348e9ffb0826af5dae3a57b0168f610a01912e87e746f4dc`
- Candidate result: `a02ec03cb88681918653fa439847b3bb747e2244cb506e203d2d27d85af224e5`

## Stage B: immediate minimum strength probe

The one registered role-swapped Arena4 pair used corpus
`593652dd655ddc67f38d9a194b9b2a44f7eef3e28d22a83c5f01abeb35b971a1`,
opening index 1, seed 820401, 512 nodes per move, depth 12, 8 MiB TT,
and two workers. Both games completed as checkmates: candidate-owner 0
lost at 154 plies and candidate-owner 1 lost at 149 plies. The pair score
was `0.0` (0–2 for the successor, mean pair score 0.0).

Transient evidence hashes:

- Stage B envelope: `dafb4f17902ee89bdf1c2492ebf56ccb9e2e95f11450789fd3b325ab67d09dac`
- Stage B result: `66641262cffeb3a888395c79d52eb7ec9691f8a45724144ba9f4016a31300e58`

## Decision

The calibrated update changed the learner and reached the registered probe,
but the immediate role-swapped pair was 0–2. Under the work-order decision
boundary this does not demonstrate a strength gain; stop this candidate here.
Do not run another pair, Arena8, confirmation, sweep, or promotion. The
project mainline should request a distinct native learning intervention.
