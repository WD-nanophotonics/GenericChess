"""Frozen 15-root common-context task pilot; no production material values."""
from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.lazy_transitions import iter_legal_successor_handles, materialize_legal_successor
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_exchange_custody import custody, synthetic_state
from scripts.audit_f24f_western_chess_perft import standard_engine, position_from_fen

PROTOCOL = ROOT / 'docs/research/SECURED_EXCHANGE_COMMON_CONTEXT_PROTOCOL.md'
PROTOCOL_SHA = '18c1d2a420487149ef1fcfcaf22a2e433dd2c2dd06c9ffbe60f12547ecec542f'
CONTEXTS = ('diagonal_open', 'orthogonal_open', 'diagonal_defended')


@dataclass
class Budget:
    seconds: float = 30
    transitions_limit: int = 20_000
    transitions: int = 0
    started: float = 0

    def __post_init__(self):
        self.started = monotonic()

    def checkpoint(self):
        if monotonic() - self.started > self.seconds:
            raise TimeoutError('common-context pilot time cap; no complete vector')

    def child(self, state, handle, compiled):
        self.checkpoint()
        if self.transitions >= self.transitions_limit:
            raise RuntimeError('common-context transition cap; no complete vector')
        self.transitions += 1
        child, _ = materialize_legal_successor(state, handle, compiled, checkpoint=self.checkpoint)
        self.checkpoint()
        return child


def context_position(compiled, game, focal_type, context):
    n = compiled.board_size
    if game == 'chess':
        template = position_from_fen('8/7k/8/8/8/8/8/K7 w - - 0 1', compiled)
    else:
        template = initial_state(compiled).position
    board = [None] * (n * n)
    inventory = [(0, 'K', 0, 0), (1, 'K', n - 1, n - 2), (0, focal_type, 3, 3)]
    inventory.append((1, 'P', 3 if context == 'orthogonal_open' else 4, 4))
    if context == 'diagonal_defended':
        inventory.append((1, 'R', 4, 6))
    for owner, tid, file, rank in inventory:
        board[rank * n + file] = Piece(owner, tid, tid)
    return replace(template, board=tuple(board), hands=(Hands.empty(), Hands.empty()), side_to_move=0)


def task_success(state, anchors, baseline):
    terminal = state.terminal_status
    if terminal.is_terminal:
        if terminal.status.value == 'no_contest':
            raise ValueError('no-contest outside task scope; no complete vector')
        return terminal.winner == 0
    return custody(state.position, anchors) > baseline


def root_score(compiled, position, budget):
    engine = semantic_engine_for(compiled)
    budget.checkpoint()
    if engine.in_check(position, 0, checkpoint=budget.checkpoint) or engine.in_check(position, 1, checkpoint=budget.checkpoint):
        raise ValueError('invalid common context; never drop or renormalize it')
    state = synthetic_state(compiled, position)
    if state.terminal_status.is_terminal:
        raise ValueError('terminal root outside frozen context law')
    anchors = {tid for tid, item in compiled.support.type_metadata.items() if item.is_anchor}
    baseline = custody(position, anchors)
    evidence = []
    for handle in iter_legal_successor_handles(state, compiled, checkpoint=budget.checkpoint):
        action = handle.action
        source = getattr(action, 'from_square', None)
        if source is None or (source.file, source.rank) != (3, 3):
            continue
        child = budget.child(state, handle, compiled)
        count = 0; guaranteed = True; refutation = None
        if child.terminal_status.is_terminal:
            guaranteed = task_success(child, anchors, baseline)
        else:
            for reply in iter_legal_successor_handles(child, compiled, checkpoint=budget.checkpoint):
                after = budget.child(child, reply, compiled); count += 1
                if not task_success(after, anchors, baseline):
                    guaranteed = False
                    if refutation is None:
                        refutation = {'action': action_to_dict(reply.action),
                                      'custody_delta': custody(after.position, anchors) - baseline,
                                      'terminal': after.terminal_status.status.value}
            if count == 0:
                raise ValueError('empty nonterminal reply set; no complete vector')
        evidence.append({'action': action_to_dict(action), 'reply_count': count,
                         'success': guaranteed, 'first_refutation': refutation})
    budget.checkpoint()
    return {'success': int(any(e['success'] for e in evidence)), 'actions': evidence,
            'position_key': repetition_identity_key(position, compiled)}


def audit(budget=None):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen protocol changed')
    budget = budget or Budget()
    chess, _ = standard_engine()
    shogi = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    rows = []; scores = {}
    for game, compiled, types in [('chess', chess, ('B', 'R', 'Q')), ('shogi', shogi, ('B', 'R'))]:
        scores[game] = {}
        for tid in types:
            values = []
            for context in CONTEXTS:
                if len(rows) >= 16:
                    raise RuntimeError('root cap exceeded; no complete vector')
                result = root_score(compiled, context_position(compiled, game, tid, context), budget)
                rows.append({'game': game, 'focal_type': tid, 'context': context, **result})
                values.append(result['success'])
            scores[game][tid] = str(sum((Fraction(v, 3) for v in values), Fraction()))
    return {'protocol_sha256': PROTOCOL_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'complete': True, 'scores': scores, 'roots': rows,
            'materialized_transitions': budget.transitions,
            'elapsed_seconds': monotonic() - budget.started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'roots'}, indent=2))
