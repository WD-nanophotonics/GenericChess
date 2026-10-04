"""Frozen root-only budget preflight; no service coefficients/goal probes."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.public_goal_intervals import PublicGame
PROTOCOL = 'docs/research/TWO_VICTIM_CONTEXT_PROPOSAL.md'
SHA = '71911618579bdab60568396a2eb8efee70f1816cc14a41de6104160eb869fedc'

def audit(report):
    started = monotonic()
    def check():
        if monotonic()-started >= 15:
            raise TimeoutError('15-second preflight cap')
    if hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest() != SHA:
        raise ValueError('proposal drift')
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    game = PublicGame(compiled)
    for df in range(0, 3):
        for dr in range(-2, 3):
            if df == 0 and dr <= 0:
                continue
            check(); rows = []
            for flip in (False, True):
                for kind in ('P', 'N', 'B', 'R', 'Q'):
                    board = [None]*64
                    pieces = [(0, 0, 'K'), (55, 1, 'K'), (27, 0, kind),
                              ((3+dr)*8+3+df, 1, 'P'), ((3-dr)*8+3-df, 1, 'P')]
                    for s, owner, t in pieces:
                        if flip:
                            s = (7-s//8)*8+s%8; owner = 1-owner
                        if board[s] is not None:
                            raise ValueError('layout collision')
                        board[s] = Piece(owner, t, t, False)
                    position = replace(initial_state(compiled).position, board=tuple(board), side_to_move=int(flip),
                        aux_state=(((0, -1), 0), ((1, -1), 0), ((2, -1), None), ((3, -1), 0), ((4, -1), 0)))
                    state = synthetic_state(compiled, position); terminal = game.terminal(state)
                    count = 0
                    if not terminal.is_terminal:
                        for _ in game.actions(state, check):
                            count += 1; report['enumerated'] += 1
                            if count > 128 or report['enumerated'] > 5000:
                                raise ValueError('choice/enum cap')
                    rows.append({'owner': int(flip), 'tracked_type': kind,
                                 'terminal': terminal.status.value, 'complete_choices': count})
            report['layouts'].append({'displacement': [df, dr], 'common_eligible': all(r['terminal'] == 'ongoing' for r in rows), 'rows': rows})
    report['eligible_layout_pairs'] = sum(r['common_eligible'] for r in report['layouts'])
    report['complete'] = True; report['seconds'] = monotonic()-started

if __name__ == '__main__':
    target = ROOT/'docs/research/data/two_victim_preflight_20261004.json'
    if not target.parent.is_dir() or target.exists():
        raise ValueError('preflight report; no unchanged rerun')
    report = {'complete': False, 'enumerated': 0, 'public_transitions': 0, 'source_probes': 0, 'layouts': []}
    try:
        audit(report)
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    paths = [PROTOCOL, 'scripts/audit_two_victim_preflight.py', 'scripts/public_goal_intervals.py',
             'scripts/audit_exchange_custody.py', 'generic_chess/rules/western_chess.py', 'generic_chess/core/semantic_executor.py']
    report['source_sha256'] = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    target.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('layouts', 'source_sha256')}))
