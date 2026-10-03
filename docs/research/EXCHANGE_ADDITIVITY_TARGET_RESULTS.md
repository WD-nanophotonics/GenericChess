# Additive capability count is not joint exchange success

The prehashed EXCHANGE_ADDITIVITY_TARGET_PROTOCOL.md reuses the frozen Chess
nonterminal support frame on base c5e10c6a122361071e2d1face4ab835d93d06c01.
Nothing is added, removed, repositioned or sampled. Restrict eligible first
actors to the existing Rooks at(3,3),(0,0), retaining the same board, custody
baseline, legal replies and terminal contract. Complete original focal evidence
reproduces exactly. No physical piece-removal map or Shapley allocation is used.

Either Rook can capture the same enemy Pawn at(0,3), followed by the sole legal
King escape. Both branches remain ongoing with net custody+1. Each actor's
individual task success is1; their joint first-turn success is1, while the
number of independently successful actors is2. This last count measures actors
with an available service, not two captured Pawns or two simultaneous services.
Every action/reply was enumerated once, grouped by actor; four public replays
are included in 219 materializations,0.125 s under the2,000/10-second cap.
Raw input/program/protocol hashes and all actions are preserved in
data/exchange_additivity_target_20261004.json.

## Three distinct quantities

For unchanged context c, let X_i(c) be the binary individual task success.
Granting first-action eligibility to a set S gives
U_any(S,c)=max_{i in S} X_i(c), with empty-set value0. Its population mean is
the probability of the union of individual success events. In contrast,
U_count(S,c)=sum_{i in S} X_i(c) counts individually successful actors. For any
fixed joint measure mu, linearity gives
E_mu U_count(S)=sum_{i in S} E_mu X_i, WITHOUT assuming independent events.
For two actors, E U_any=E X_A+E X_B-Pr(X_A=1,X_B=1).

Two chosen equiprobable finite laws demonstrate the missing joint information:

| Law | Context success pairs | E X_A | E X_B | E U_any | E U_count | A increment given B |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Overlap | (1,1),(0,0) | 1/2 | 1/2 | 1/2 | 1 | 0 |
| Disjoint | (1,0),(0,1) | 1/2 | 1/2 | 1 | 1 | 1/2 |

Identical marginal scores therefore cannot identify joint success or marginal
union contribution. This is target non-equivalence under explicit measures,
not a demand for uniquely rule-selected weights, and not physical deletion.

## Consequence for the static prior

Adopt the conditional linearity identity as a precise possible meaning of an
additive capability statistic. Do NOT adopt U_count as strategic utility or a
material formula merely because it is additive. Counting individually useful
resources can be a declared approximation, but redundant access to one victim
shows why it is not guaranteed net custody, joint success or physical-token
marginal value. These alternative targets must not be interchanged in validation.

Even that identity requires a common JOINT population. The current single-focal
type-replacement law supplies type-conditioned marginals in different inventory
backgrounds at one source. It has not established compatible per-piece marginals
under one actual inventory population, source averaging, type exchangeability,
or transfer to held/midgame resources. Do not silently infer a type-local
sum(n_t*v_t) from linearity without those additional approximation premises.

The original binary task and sampler remain unchanged. Its static material use
needs an independently motivated target/population and frozen predictive loss.
The daily advisor question can now ask whether a capability-count approximation
has a defensible intended use; no more R-support or redundancy fixtures are
needed simply to re-establish these distinctions. Engine profiles and sealed
Xiangqi references were not changed.
