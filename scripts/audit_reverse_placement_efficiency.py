"""Exact shared-normalizer comparison; no random proposals or task labels."""
from fractions import Fraction
import hashlib
import json
from math import comb
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_dead_placement_conditioning import completion_count
from scripts.audit_secured_exchange_common_context import Budget

PROTOCOL = ROOT / 'docs/research/REVERSE_PLACEMENT_EFFICIENCY_PROTOCOL.md'
PROTOCOL_SHA = '75eac94e0b4e5ae24e0212a090c8348d3b5cd8bc7e67eb27480bcc595d7ced37'
GROUPS = ((0, 'L'), (0, 'N'), (1, 'L'), (1, 'N'))


def unrestricted_layouts(cells):
    return comb(cells, 2) * comb(cells - 2, 2) * comb(cells - 4, 2) * comb(cells - 6, 2)


def audit(budget=None):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen reverse-placement protocol changed')
    budget = budget or Budget(seconds=10)
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    if compiled.board_size != 9:
        raise ValueError('declared 9x9 Shogi scope required')
    masks = [compiled.support.empty_mobility[kind][owner] for owner, kind in GROUPS]
    expected = (lambda r: r <= 7, lambda r: r <= 6, lambda r: r >= 1, lambda r: r >= 2)
    for mask, allowed in zip(masks, expected):
        if any(bool(mask[square]) != allowed(square // 9) for square in range(81)):
            raise ValueError('actual restricted mobility scope differs')
    other_types = {p.current_type_id for p in initial_state(compiled).position.board
                   if p and p.current_type_id not in ('P', 'L', 'N')}
    if any(not all(compiled.support.empty_mobility[kind][owner]) for kind in other_types for owner in (0, 1)):
        raise ValueError('additional intrinsic dead-placement restriction')
    cells = tuple(tuple(group for group, mask in enumerate(masks) if mask[square]) for square in range(81))
    w81 = completion_count(cells, (2, 2, 2, 2), budget.checkpoint)
    u63 = unrestricted_layouts(63)
    if not 0 < w81 <= unrestricted_layouts(81):
        raise ValueError('invalid full-board constrained count')
    ratio = Fraction(u63, w81)
    budget.checkpoint()
    return {'protocol_sha256': PROTOCOL_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'counter_sha256': hashlib.sha256((ROOT / 'scripts/audit_dead_placement_conditioning.py').read_bytes()).hexdigest(),
            'ruleset_fingerprint': initial_state(compiled).position.ruleset_fingerprint,
            'complete': True, 'W81': w81, 'U63': u63,
            'raw_acceptance_ratio_reverse_to_original': str(ratio),
            'reverse_improves_raw_acceptance': ratio > 1,
            'coefficient_state_bound': 81, 'physical_cells': 81,
            'other_initial_types_unrestricted': sorted(other_types),
            'elapsed_seconds': monotonic() - budget.started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result, indent=2))
