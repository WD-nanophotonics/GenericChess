"""Reproduce the actual material decomposition of one frozen seed102 exchange.

Run from repository root after extracting evidence.zip into this record folder.
No independent task utility, strength or reference-score claim follows.
"""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path.cwd()))
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.core.actions import BoardMove
from generic_chess.core.coordinates import Square
from generic_chess.core.transition import initial_state, apply_action
from scripts.research_record import write_record

p = Path(__file__).resolve().parent
cases = json.loads((p / 'opening-preflight.json').read_bytes())['cases']
witness = next(x for x in json.loads((p / 'exchange-frontier.json').read_bytes())['rows']
               if x['seed'] == 102 and x['delta']['v3'])
c = compile_ruleset_for_execution(ruleset_from_dict(
    next(x['rules'] for x in cases if x['seed'] == 102)))
profile, scope = build_semantic_opportunity_profile(c, EvaluationConfig())


def action(row):
    return BoardMove(Square(**row['from_square']), Square(**row['to_square']),
                     row['promotion_target_id'])


def parts(state):
    board = sum((1 if piece.owner == 0 else -1) *
                profile.board_value_by_type[piece.current_type_id]
                for piece in state.position.board if piece)
    hand = sum((1 if owner == 0 else -1) * count *
               profile.hand_value_by_base_type[tid]
               for owner, h in enumerate(state.position.hands)
               for tid, count in h.counts)
    return dict(board=board, hand=hand, total=board + hand)


root = initial_state(c)
a = apply_action(root, action(witness['capture']), c)
b = apply_action(a, action(witness['reply']), c)
rows = [parts(s) for s in (root, a, b)]
assert rows[-1]['total'] - rows[0]['total'] == 1273
values = {t: dict(board=profile.board_value_by_type[t],
                  hand=profile.hand_value_by_base_type[t],
                  raw=scope['types'][t]['raw'], curves=scope['types'][t]['curves'])
          for t in ('B', 'X')}
report = dict(
    scope='Exact material decomposition at one frozen actual B-captures-X/recapture witness. No independent utility or reference-score validation.',
    values=values, actual_prefix=rows, delta_board=670, delta_hand=603,
    reported_net=1273)
write_record(p / 'exchange-decomposition.json', report)
