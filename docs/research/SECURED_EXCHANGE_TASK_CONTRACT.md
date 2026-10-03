# Secured-exchange task: conditional assumptions and exact first checks

## Question and advisor decision

The earlier first-action service proxy counted routes without adversarial
survival. Can a new objective respect controllable options without pretending
that rules uniquely determine the context distribution?

[Dot consultation](https://nanomelon.slack.com/archives/C0C6L21UU20/p1791028173607329)
has REQUEST_ID `GC-SLACK-20261003-204910-5111c7bf` and committed evidence base
`9387821b709ef84fdf5e793d55179e2511800ae5`. Dot independently read that published
mainline; it did not inspect the new local outputs. Its candidate is an inference,
not a sourced theorem or a claim of material-benchmark success.

Adopt its distinction: an approximate prior may use independently motivated,
explicit modelling assumptions. Requiring a uniquely rule-selected measure is
stronger than that objective. Merely naming assumptions still supplies neither
predictive evidence nor a derivation of additive piece prices. Defer the proposed
placement ensemble, fixed inventory, equal-token utility, two-ply boundary and
static material interpretation until their separate checks.

Dot's second post supplies two primary pointers. Barreto et al.'s
[Successor Features for Transfer in Reinforcement Learning (2017)](https://proceedings.neurips.cc/paper/2017/file/350db081a661525235354dd3e19b8c05-Paper.pdf)
separates environment dynamics from task rewards. This is conceptual support
for explicit assumptions, not evidence for this exchange utility or a proposal
to train successor features. [Stockfish position.cpp](https://github.com/official-stockfish/Stockfish/blob/master/src/position.cpp)
implements see_ge with supplied PieceValue entries; it does not derive those
prices. Both sources were independently opened; Stockfish's moving branch is
not a frozen experiment reference. Neither source validates this candidate.

## Declared objective

Observe context c, choose a legal first action by the focal token, and let the
opponent choose any legal reply. Success means a positive change in own-minus-
opponent ordinary-token custody and no acting-side terminal loss. A terminal
win counts as success; terminal successors stop immediately. A nonterminal action
needs its complete nonempty reply set. No focal action means zero task success,
not a game draw. Draws, losses and restart/no-contest outcomes need an explicit
contract before using real terminal contexts. Dot's second post clarifies win=1,
draw/loss=0; no-contest remains excluded explicitly. These are task conventions.

The score is an explicit weighted context average of max-action/min-reply binary
success. Context is known before action selection. Weights and the custody utility
are declared model choices. Legality, custody changes and terminal outcomes come
from executable rules. No new coefficient or Xiangqi human reference is used.

## Exact algebra result, 2026-10-03

`scripts/secured_exchange_contract.py` uses rational arithmetic on two observed,
equiprobable contexts. A has complementary successful actions; B has one action
that succeeds in both. These are finite task fixtures, not legal Chess positions.

| Check | Exact score |
| --- | ---: |
| Adaptive choice for A / broad action for B | 1 / 1 |
| Add losing option and duplicate physical description to A | 1 |
| Before / after a genuinely new successful context | 1/2 / 1 |
| Add a legal opponent refutation in one context | 1/2 |
| Incorrect action average / max after averaging for A | 1/2 / 1/2 |

Conflicting physical descriptions, incomplete/empty reply evidence and weights
that need hidden renormalization are rejected. Even an already successful option
does not mask another incomplete enumeration. This establishes the implementation
contract and its distinction from the rejected route/policy averages. It does not
identify weights or prove a useful relative material prior.

A separate declared finite inventory sequence (+1, 0, -2) is positive after two
plies and negative after three. It illustrates the horizon objection without
claiming a certified Chess/Shogi position or rejecting a population approximation.

## Public legal-action custody witnesses

Before projecting a type vector, `scripts/audit_exchange_custody.py` freezes three
synthetic contexts. Chess uses FEN `7k/8/8/3p4/3R4/8/8/K7 w - - 0 1` and R d4xd5.
Shogi places owner-0 K at (0,0), R at (3,3), owner-1 K at (8,8), P at (3,4),
with owner 0 to move and empty hands, and chooses the unpromoted R capture.
The third context adds an owner-0 held Pawn and chooses its legal drop at (4,4).
Coordinates are zero-based file/rank. Synthetic history is explicitly reset to
that context; there is no reachable-game population claim.

The complete public legal-action list establishes eligibility; public apply_action
supplies the transitions. Anchor metadata comes from compiled semantic support.
Board and hand tokens are counted together under their current owner.

| Action | Custody balance delta | Own hand before / after |
| --- | ---: | ---: |
| Chess removal capture | +1 | 0 / 0 |
| Shogi capture to hand | +2 | 0 / 1 |
| Shogi hand-to-board drop | 0 | 1 / 0 |

All immediate successors are ongoing. After freezing these witnesses, the
audit also exhausted their legal opponent replies: 3 Chess, 3 Shogi capture,
and 4 Shogi drop replies. The fixed capture actions retain task success under
every reply; the fixed drop does not. Total enumeration was 123 actions in
0.156 s locally under a 1000-action/30-second cap. This checks the chosen utility's
mechanics: removal and transfer differ, while deployment preserves custody.
It does not show that those units are strategically appropriate. This is a
complete reply check for three selected actions, not a max over all focal
actions, a context-population estimate, or a relative type vector.

## Next falsifier, frozen before numerical type results

The three fixed-action reply checks above passed. Before a type score, exhaust
all focal actions and their legal replies under the same frozen context measure;
terminal successors must bypass reply enumeration. Preserve exact custody and
terminal evidence and fail on incomplete coverage. Limits: no more than
16 listed roots, 20,000 distinct legal transitions, 30 seconds total, one process.
No adaptive horizon, piece factor or reference inspection is allowed.

Before estimating a type vector, specify a common context law and account for
invalid configurations without type-specific renormalization. A frozen validation
distribution/search frontier and error criterion are still required. Keep Xiangqi
human values sealed; no repeat of V2H, first-action distance tuning or R5 expansion.
