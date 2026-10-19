# Raw capability scale vs saved normalized profile — 2026-10-20

## Question and scope

On the exact-signature cross-rule match `521004:P` / `522008:A` (both raw
capability score `1.3468429710250438`), does replacing each saved normalized
static profile with its unnormalized raw capability scores alter fixed-budget
Native choices on the four already-saved roots? This is a finite search
sensitivity check, not a price-utility or cross-rule transfer test. No games,
training, new roots, or product/default changes were made.

## Frozen inputs and method

The paired arms are the saved normalized board/hand profile and raw capability
scores for all non-anchor types, with hand values multiplied by the existing
`EvaluationConfig.hand_weight`; anchors remain zero. Both use the existing
`LearnableMaterialCheckpoint` representation (`material_scale=256`,
`value_scale=10`), generated rules and saved roots. Conditions are identical:
D4 maximum, 4096-node cap, 30-second per-query ceiling, Q0, TT0, and root-window
pruning off. The producer also checks the loaded rule/profile/root SHA256s,
reconstructed root-state hashes, input immutability, and root-action legality.
All four roots hit the 4096-node cap at D3; none completed D4.

The original plan had a malformed `521004` root-manifest digest. Its first
escalated attempt stopped at the pre-search SHA assertion with zero input/root
rows. That exact failed frontier is retained as
`data/raw_profile_scale_521004_522008_20261020/attempt_manifest_sha_failure.json`.
The plan was corrected to the verified full digest before the sole search run.
A preceding restricted-run attempt was manually interrupted before an output
record existed; its cause was not established and it contributes no evidence.

## Results

The corrected run completed four roots/eight searches in 0.204 seconds of
producer-measured wall time. Action and PV matched on all four roots; every PV
contained three legal plies on independent `GameSession` replay. Quantized
board weights in compiled type order `(K,P,A,B)` were:

| Rule | Saved normalized | Raw capability scale |
| --- | --- | --- |
| 521004 | `(0,157,256,355)` | `(0,345,560,777)` |
| 522008 | `(0,400,256,105)` | `(0,539,345,142)` |

Quantized hand weights in that same order were `(0,142,230,320)` vs
`(0,310,504,700)` for 521004 and `(0,360,230,95)` vs `(0,485,310,128)` for
522008. The scores changed on all roots (normalized/raw): `-299/-653`,
`497/1087`, `505/681`, and `465/627`. These are evaluator scores under two
scales, not rewards, WDL, or usefulness.

Exact input hashes: rule/profile/root-manifest for 521004 are
`f7bd62cd5ad5abbf31740971161a1ac30e693e5d681d367b5ce09b96f606f16c`,
`90ab29a9810a4b636ed5b6c190991584cfedf93633b17d3cba6d742529d0fd03`, and
`3d8f6cd488dfaba3525a91797edc8672d48c3d1a4b037f9a9d0aa05a2462da07`.
For 522008 they are
`9f101d613d26e10ba51e528678463bf77287a638fd8569f81fcf7dbdd1c89123`,
`ba6da0917c9b675c41a18235765e8bd704331ae6c8dc8063e4342a5129af8441`, and
`b06a6a837e5571ce781015a7bca5387fe89703daf080546fa4825ea55a57ff04`.
The corrected plan SHA is `31c6f3b301c0b9eba93bcf50a3547f73a9b1bc690de4005a8518e554080e217f`;
the result SHA is `b41d67c3862d94032cbb985eee14a4fecf79eb0983dfcfd516c1387f3bb5d50f`.

## Decision

On these four frozen roots, raw-vs-normalized scale changed score magnitudes
but neither selected action nor the first three PV plies under the shared node
cap. This closes only this pair's finite action/PV sensitivity question. It
does not show the profiles equivalent, the raw scale correct, or either arm
more useful. Retain the current per-ruleset normalized profile and do not add
games, training, a broader price panel, or a product/default change on this
result alone. Return to a distinct unfamiliar-rule search contract whose
opposite outcomes could change an implementation choice.

Evidence and reproducer: `data/raw_profile_scale_521004_522008_20261020/`.
