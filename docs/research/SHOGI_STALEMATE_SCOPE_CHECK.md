# Standard Shogi no-move terminal scope

## Direct source and code check

The current `build_standard_shogi_ruleset()` sets
`stalemate_result="draw"`. Before using exact Shogi terminal W/D/L as
a material-prior reference, compare that setting with the primary
[Japan Shogi Association match rules](https://www.shogi.or.jp/match/taikyoku_rules/)
(rules page, current revision linked there). Article 2 defines the
objective as checkmating the opponent's King; Article 6 lists ending
by mate or resignation, with further cases for entering-King and rule
violations. The page does not specify a draw on a nonchecked position
with no legal move. Its stated no-contest procedures concern repetition
and entering-King conditions, not stalemate.

This is a **scope mismatch**, not evidence for silently changing the
RuleSet to another terminal result. A no-move, noncheck position may be
rare or outside ordinary reachable play, and official adjudication of
that constructed edge case is not established by the cited rule text.
The present project product has a definite draw convention; the
official source does not validate it. The Xiangqi diagnostic RuleSet
separately declares no-move loss and tests it, while Western Chess uses
the normal stalemate draw rule. These different terminal conventions
matter for any proposed game-independent mobility-to-value argument.

## Decision

Do not change Shogi gameplay on ambiguous evidence, and do not use the
local Shogi no-move draw as an official ground-truth label. This does
not block the current static material-prior investigation: its Shogi
control compares board-mode structure, and the current mainline
explicitly excludes full historical adjudication. If a later
goal-linked objective depends on no-move outcomes, first specify its
Shogi terminal contract and obtain a decisive rules source or treat
this edge as an explicit model choice.
