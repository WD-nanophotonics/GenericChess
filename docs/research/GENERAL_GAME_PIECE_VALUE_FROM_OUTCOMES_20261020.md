# Outcome-derived piece values are rule- and distribution-specific — 2026-10-20

## Decision question

Does recent empirical valuation work provide numeric targets or a new evaluation
protocol for the complete generated-rule price objective?

## Source and method

The primary source is *Inferring Piece Value in Chess and Chess Variants*
([arXiv:2509.04691](https://arxiv.org/abs/2509.04691)). It estimates logistic
outcome coefficients for material imbalance in Chess, Chess960, Atomic,
Antichess and Horde. The observational arm uses Lichess human games; this
project does not use its human records or values as labels, validation data or
priors. A separate Stockfish 17.1 self-play arm uses modified standard and
Chess960 opening positions with piece removals, several engine settings, five
seconds per move and a depth-seven cap.

## Findings relevant to this project

The authors report self-play estimates that differ from their Lichess-derived
values and list the discrepancy as unresolved. Their self-play model includes
engine-setting and first-player terms; the authors also note that values depend
on the chosen rules and tested position distribution. The article's proposed
future work includes evaluating randomly generated positions and controlled
piece interventions. Those proposals do not establish transport to our
generated rules, auxiliary state, drops or histories.

## Decision

Do not import empirical numeric ratios, fit human labels or change the current
price candidate/default. The methodological warning agrees with the existing
PRIMARY design: keep positions/rules and resources explicit, compare candidates
in paired full-history games against fixed foes, and retain UNKNOWN. Existing
project panels already instantiate that controlled comparison; this source
does not justify duplicating them or starting a new learner. Reopen only for a
concrete same-rule decision that the current paired design cannot answer.
