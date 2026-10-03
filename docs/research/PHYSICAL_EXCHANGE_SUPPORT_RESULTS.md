# Conditional exchange support: bounded negative evidence

The unchanged physical-placement law and global net-custody task were tested
under the prehashed PHYSICAL_EXCHANGE_SUPPORT_PROTOCOL.md. Only focal R was
scored; all ordinary current types still participated in the common quiet screen.
Seed 20261003, Chess then Shogi, eight admitted frames or first positive root,
128 proposals per game, 20k transitions and 30 seconds. Every focal action and
opponent reply was enumerated. These are existence checks, not sample means.

| Game | Proposals | Admitted/scored frames | Exact positive roots | Status |
| --- | ---: | ---: | ---: | --- |
| Chess | 64 | 8 | 0 | No witness within frozen cap |
| Shogi | 128 | 5 | 0 | Incomplete: proposal cap before eight frames |

Chess first-failure rejection counts were own-anchor check 37 and nonmoving-
anchor check 19. Shogi counts were dead nonfocal placement 101, own-anchor check
12 and nonmoving-anchor check 10. First-failure counts are not a full overlap
classification. All thirteen scored roots and their negative action/reply
evidence are retained in data/physical_exchange_support_20261003.json.
3,098 materializations completed in 1.422 s. No larger run or second seed followed.

There is no observed support witness and no useful coefficient vector from this
run. This does not prove the conditional population has zero support. Shogi's
cap exhaustion is explicitly incomplete, never relabelled a population zero.
Sequential stopping would also make averages inappropriate had a witness appeared.

## Exact conditioning check before an optimisation

Dead-placement rejection suggests redrawing L/N while retaining each Pawn frame.
That shortcut changes the joint law unless the Pawn frame is weighted by its
number of valid completions. A separate prehashed exact count checked this on
the original Shogi frame plus all five newly admitted frames, without new draws
or game-value calculations. The cell-polynomial coefficient method counts the
two L/N tokens of each owner, with their actual allowed ranks; fourteen other
tokens have constant completions and cancel. The unrestricted denominator is
9,759,694,636,440 in every frame.

| Frame | Valid L/N physical completions | Conditional nondead probability |
| --- | ---: | ---: |
| Original | 1,933,458,686,712 | 0.198106 |
| Support proposal 2 | 1,651,429,629,528 | 0.169209 |
| Support proposal 4 | 2,273,024,049,660 | 0.232899 |
| Support proposal 101 | 2,359,991,755,296 | 0.241810 |
| Support proposal 105 | 1,796,932,493,832 | 0.184118 |
| Support proposal 106 | 2,179,380,498,372 | 0.223304 |

The raw exact fractions and source/input hashes are in
data/dead_placement_conditioning_20261003.json. Six counts took 0.016 s with at
most 81 coefficient states per cell. An independent miniature exhaustive oracle
checks the coefficient operation. A separate equal-parent/equal-child-space
example gives globally conditioned parent weights 1/4,3/4, while parent-fixed
redraw leaves 1/2,1/2. Production completion counts demonstrably differ, so the
unweighted shortcut is rejected. This is not a quiet-screen acceptance estimate.

## Decision and next uncertainty

Keep the original unbiased sampler, negative frames and task contract. Execution
is already inexpensive; sampler optimisation alone would not establish signal,
an appropriate strategic population or a static additive material interpretation.
Do not install zeros, tweak density/horizon/source, change the score to local
survival, or average these sequential support records. A future experiment needs
a separately justified strategic population or a specific structural support
argument before another score batch. The daily advisor window can review that
scientific choice; independent theory and semantic checks do not wait for it.
No engine evaluation or Xiangqi human holdout was changed.
