# Prospective first-quiet exchange pilot

Freeze before root selection or outcomes,2026-10-06. Changed premise from the
closed terminal-window tests: the target is the explicitly declared finite
exchange ending at the FIRST actual legal quiet action. Captures continue;
real SESSION terminals take precedence and are recorded separately. No
stand-pat/pass, forced quiet at check, terminal override, price-based defender
choice or reuse/deepening of an exposed root. This is a development mechanism
pilot, not WDL or natural-game strength validation.

Population: synthetic Western root with owner0K/R and owner1K/N/B, no held
pieces, castling, en-passant, promotions or Pawn. Own King central c3..f6,
N/B on distinct adjacent squares, enemy King on an unoccupied corner, R on
any remaining square. Use SHA256 modular picks with namespace
GenericChess/first-quiet/v1/proposal/<i>/<label> and fixed row-major options.
First eligible among128 proposals, no replacement: previous mover not checked,
current mover checked, ongoing root, two or three COMPLETE root actions,
at least two distinct captured ordinary types. No controller disagreement,
later closure, proxy preference or favorable label filter. This is an openly
conditioned exchange population, not a claim about all Chess.

One compiled ruleset. Fresh full history and zero auxiliary rights. At every
nonterminal capture node enumerate all genuine legal choices, materialize ALL
children and retain full public states. A quiet edge terminates only after
applying that legal action. Each capture reduces nonroyal board count by one;
with three ordinary tokens, a path has at most three captures before a quiet
edge or genuine terminal. This guarantees finite structure, NOT affordable
closure. The root and all continued capture nodes retain every action, even
when a controller would reject it; no state/TT merge.

Controllers are fixed exact depth1/q0 material choices with royal anchoring,
token bound30 and full canonical/tie sets: two existing exact duration laws,
unit and zero. At root, save all one-ply children and selections to a separate
prelabel record BEFORE recursing or computing proxy labels. At later owner0
nodes freeze each one-ply choice table before visiting descendants. No fitting
or goal-aware adjustment. Defender always retains all actions. Controller
canonical outcomes and every allowed controller tie policy are separately
aggregated; a union of tie outcomes is conservative for worst-case comparison.

Every quiet leaf records the five signed native-mode inventory counts P/N/B/R/Q
from ROOT owner0 perspective, without weighting. Preserve outcome/action/path
incidence; actual terminals stay a separate class. Compare complete material
outcome sets only if all controller outcomes belong to the quiet class, using
the sufficient coordinate-set relation in OUTCOME_SET_ORDER_CONTRACT.md in
both directions. Weak dominance is not strict gain. Incomparability is valid.
Depth1 scored children are not themselves new information: distinguish actual
continued capture states beyond that cutoff from quiet children already seen.
Without such increment, report implementation control, not quality evidence.

Family hard caps:128 proposals,128 public transitions,5000 enumerated entries
(returned lists plus membership checks),128 actions/list,30sec TOTAL including
optional independent replay, one compilation. Replay has separate128 author
pushes/5000 legal entries but uses the SAME clock remainder,0 additional Core
events. Source acquisition/table queries0. Source replay may use only the
existing pinned python-chess; full board/actor/history/rights/action checks
are required, SESSION-terminal rules explicitly distinguished from author
insufficient-material draws. No full WDL labels. The cap failure closes this
pilot, retains partial evidence and never replaces root or resets counters.
