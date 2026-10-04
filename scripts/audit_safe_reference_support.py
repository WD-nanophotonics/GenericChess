"""Public capture witnesses exclude safe-reference deployment support; no Y."""
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_from_dict
from generic_chess.core.transition import apply_action
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_f24f_western_chess_perft import standard_engine
from scripts.audit_post_capture_scope import state_evidence
from scripts.audit_secured_exchange_common_context import Budget
from scripts.generate_capability_corpus import own_counts
from scripts.label_joint_capability_corpus import INPUT, INPUT_SHA, load_root

PROTOCOL = ROOT / 'docs/research/SAFE_REFERENCE_SUPPORT_PROTOCOL.md'
PROTOCOL_SHA = '9960963a4d921bab11116c0253018a27a121a2d5437854d42a68720e78598c41'


def audit(budget=None):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA or hashlib.sha256(INPUT.read_bytes()).hexdigest() != INPUT_SHA:
        raise ValueError('frozen support protocol or corpus changed')
    budget = budget or Budget(seconds=10, transitions_limit=12)
    corpus = json.loads(INPUT.read_text())
    if not corpus['complete']:
        raise ValueError('complete frozen witnesses required')
    games = {'chess': standard_engine()[0], 'shogi': compile_ruleset_for_execution(build_standard_shogi_ruleset())}
    rows = []
    for game, compiled in games.items():
        for deployment in corpus['games'][game]['deployment']:
            budget.checkpoint()
            selected = deployment['selected']; kind = deployment['victim_type']
            parent = load_root(compiled, game, selected['parent'])
            action = action_from_dict(selected['selected_action'])
            target = action.to_square.rank * compiled.board_size + action.to_square.file
            victim = parent.position.board[target]
            if victim is None or victim.owner != 0 or victim.current_type_id != kind or compiled.support.type_metadata[kind].is_anchor:
                raise ValueError('not a declared ordinary capture witness')
            if budget.transitions >= budget.transitions_limit:
                raise RuntimeError('public support replay transition cap')
            child = apply_action(parent, action, compiled); budget.transitions += 1
            budget.checkpoint()
            expected = own_counts(compiled, parent.position); expected[kind] -= 1
            if state_evidence(child, compiled) != selected['child'] or child.terminal_status.is_terminal or child.position.hands[0].total() or own_counts(compiled, child.position) != +expected:
                raise ValueError('capture child scope or evidence mismatch')
            rows.append({'game': game, 'victim_type': kind, 'action': selected['selected_action'],
                         'safe_parent_excluded': True, 'ongoing_capture_support': True,
                         'own_board_count_delta': {kind: -1}})
    if len(rows) != 12:
        raise ValueError('all twelve support strata required')
    return {'protocol_sha256': PROTOCOL_SHA, 'input_sha256': INPUT_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'complete': True, 'rows': rows, 'materialized_transitions': budget.transitions,
            'elapsed_seconds': monotonic() - budget.started}


if __name__ == '__main__':
    result = audit()
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2))
