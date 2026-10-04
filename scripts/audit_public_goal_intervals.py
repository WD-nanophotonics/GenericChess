"""Frozen existing Chess controls for the public-transition interval observer."""
from hashlib import sha256
import json
from pathlib import Path
from time import monotonic
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.core.terminal import TerminalStatus
from scripts.audit_chess_root_terminal_labels import FEN
from scripts.f156_known_game_shallow_search_equivalence import _western_pair, _western_state
from scripts.public_goal_intervals import PublicGame, observe

ROOT = Path(__file__).resolve().parents[1]


def audit():
    started = monotonic()
    compiled, _ = _western_pair()
    root = _western_state(compiled, FEN)
    construction = monotonic()-started
    game = PublicGame(compiled)
    controls = {'initial': observe(initial_state(compiled), game, depth=1),
                'existing_mate_root': observe(root, game, depth=1)}
    transitions = 0
    terminal_controls = {}
    for action in legal_actions(root, compiled):
        child = apply_action(root, action, compiled)
        transitions += 1
        status = child.terminal_status.status
        if status in (TerminalStatus.CHECKMATE, TerminalStatus.STALEMATE) and status.value not in terminal_controls:
            terminal_controls[status.value] = observe(child, game, depth=0)
        if len(terminal_controls) == 2:
            break
    if controls['initial']['interval'] != (-1, 1) or controls['existing_mate_root']['interval'] != (1, 1):
        raise ValueError('frozen Chess interval control mismatch')
    if terminal_controls['checkmate']['interval'] != (1, 1) or terminal_controls['stalemate']['interval'] != (0, 0):
        raise ValueError('terminal control mismatch')
    return {'protocol_sha256': sha256((ROOT/'docs/research/PUBLIC_GOAL_INTERVAL_PROTOCOL.md').read_bytes()).hexdigest(),
            'declaration_addendum_sha256': sha256((ROOT/'docs/research/PUBLIC_GOAL_INTERVAL_DECLARATION_ADDENDUM.md').read_bytes()).hexdigest(),
            'observer_sha256': sha256((ROOT/'scripts/public_goal_intervals.py').read_bytes()).hexdigest(),
            'ruleset_fingerprint': compiled.ruleset_fingerprint,
            'construction_seconds': construction, 'existing_root_fen': FEN,
            'terminal_control_selection_transitions': transitions,
            'controls': controls, 'terminal_controls': terminal_controls}


if __name__ == '__main__':
    result = audit()
    Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result,indent=2))
