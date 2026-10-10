"""Frozen common-time controls; finite-depth regret is diagnostic, not WDL."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from time import perf_counter
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.search_backend_comparison import (
    CASES, VALUES, CoreBoard, ChessBoard, ShogiBoard, minimal_ab,
    iterative_minimal, supported_search, audit_pair,
    build_builtin_ruleset, compile_ruleset_for_execution,
)
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.evaluation.config import MATE_THRESHOLD


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = dict(schema=1, cases=CASES, values=VALUES, budgets=[0.25, 1.0, 4.0], repeat=2,
                  scope='Exposed development roots; finite D4 material/control teacher, not true value or strength',
                  source_sha256={name: hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest()
                                 for name in ['search_backend_comparison.py', 'search_attribution_utility.py']},
                  references=[], rows=[])
    compiled = {game: compile_ruleset_for_execution(build_builtin_ruleset(name))
                for game, name in [('chess', 'western_chess'), ('shogi', 'standard_shogi')]}
    def save():
        args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    for case in CASES:
        core = CoreBoard(case, compiled[case['game']])
        specialized = ChessBoard(case) if case['game'] == 'chess' else ShogiBoard(case)
        provider = NativeSemanticLegalityProvider.try_create(compiled[case['game']], strict=True)
        if provider is None:
            raise RuntimeError('native control unavailable; record failure, do not substitute silently')
        native = CoreBoard(case, compiled[case['game']], provider=provider)
        audited = audit_pair(core, specialized, 1)
        audit_pair(native, specialized, 1)
        reference = minimal_ab(specialized, 4, seconds=10, node_limit=500000)
        result['references'].append(dict(case=case['id'], audited_states=audited, **reference))
        save()
        for seconds in result['budgets']:
            for repeat in range(2):
                arms = [('minimal_core', core), ('minimal_specialized', specialized),
                        ('minimal_native_legality', native), ('supported_core', core),
                        ('supported_native_legality', core)]
                if repeat%2:
                    arms.reverse()
                selected = []
                # All timed calls finish before finite-depth selected-child checks.
                for name, board in arms:
                    row = (supported_search(board, 12, seconds, 1000000,
                                provider if name == 'supported_native_legality' else None)
                           if name.startswith('supported_') else
                           iterative_minimal(board, seconds=seconds, max_depth=12))
                    selected.append(dict(case=case['id'], backend=name, seconds=seconds, repeat=repeat, **row))
                    print(case['id'], seconds, repeat, name, row['reason'],
                          row.get('completed_depth', row.get('statistics', {}).get('completed_depth')),
                          row['move'], flush=True)
                for row in selected:
                    moves = dict(specialized.actions())
                    row['legal'] = row['move'] in moves
                    row['finite_D4_regret'] = None
                    if row['legal']:
                        child_case = dict(case, moves=(case['moves']+' '+row['move']).strip())
                        child_board = ChessBoard(child_case) if case['game'] == 'chess' else ShogiBoard(child_case)
                        child = minimal_ab(child_board, 3, seconds=5, node_limit=500000)
                        row['selected_child_D3'] = child
                        if child['reason'] == reference['reason'] == 'completed_depth':
                            value = -child['score']
                            if abs(value) >= MATE_THRESHOLD:
                                value += -1 if value > 0 else 1
                            row['selected_value_D4'] = value
                            row['finite_D4_regret'] = reference['score']-value
                            if row['finite_D4_regret'] < 0:
                                raise AssertionError('selected complete child exceeds exact full-root reference')
                    result['rows'].append(row)
                save()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
