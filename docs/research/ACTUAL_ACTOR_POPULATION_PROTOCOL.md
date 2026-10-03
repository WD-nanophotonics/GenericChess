# Actual-actor population bridge: predeclared exact audit

Base: 659ae23a0bfc3eed1cec2a802fc31d0f6f98aeb1. No new Chess/Shogi
transitions, score batch, coefficients or human references are requested.

Question: can a shared population of unchanged physical contexts define
type-local actor-success means without the focal replacement transfer? Which
source weights and inventory restrictions does the resulting identity require?

Define a finite probability law Q over contexts c. In each context identify
actual eligible ordinary actors by (owner, source); do not delete or replace
pieces. Their binary X_i(c) is a fully evaluated declared task. A finite audit
uses abstract flags, not certified Chess/Shogi labels. N_t(c) counts actors of
type t and Y(c)=sum_i X_i(c). Complete labels are required even at zero mass.

For fixed inventory N_t=n_t>0, sample c from Q and one existing actor uniformly
among that type. Define v_t=E_Q[sum_{i:type t} X_i/n_t]. Then E_Q Y=sum_t n_t v_t.
Decompose this marked-actor mean by source using its actual conditional
probability, not uniform supported-source weights. The audit will enumerate
three equally weighted contexts with one A and one B each:

| Context | A source / X | B source / X |
| --- | --- | --- |
| c0 | left / 1 | middle / 0 |
| c1 | left / 1 | right / 1 |
| c2 | middle / 0 | right / 1 |

The second declared law has two equiprobable inventory regimes:

| Context | A flags | B flags |
| --- | --- | --- |
| d0 | one actor: 1 | one actor: 0 |
| d1 | two actors: 0,0 | one actor: 1 |

For this variable inventory, compare two ways of defining a type mean:
(a) draw a context then a uniformly random actor among all its actors, condition
on type; (b) pooled Q-weighted type successes divided by Q-weighted type counts.
Test their products with E_Q N_t against E_Q Y. Also evaluate the squared error
of the pooled static count predictor sum_t N_t(c)v_t against Y(c). No threshold
will be selected from these results; this is a measure/estimand certificate,
not predictive validation or a fitted material formula.

Reject malformed, unnormalized, negative or incomplete evidence. Use exact
Fraction arithmetic, at most five listed contexts total, one process, no game
search or randomness. Any incomplete audit supplies no population certificate.
Record protocol/program hashes and exact outputs. A passing audit licenses
only the conditional population identities; strategic utility, an inexpensive
game population, held/promoted type scope and deployment transfer remain open.
