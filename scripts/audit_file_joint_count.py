"""Count joint Pawn/L/N configurations without proposals or value labels."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_reverse_placement_efficiency import GROUPS, unrestricted_layouts
from scripts.audit_secured_exchange_common_context import Budget

PROTOCOL = ROOT / 'docs/research/FILE_JOINT_COUNT_PROTOCOL.md'
PROTOCOL_SHA = '6da25d3a80e81775bdf659d5fa733371860d1effa484c0059fcee188d009d882'


def multiply(left, right, quotas, checkpoint=lambda: None):
    result = {}
    for a, ca in left.items():
        checkpoint()
        for b, cb in right.items():
            target = tuple(x + y for x, y in zip(a, b))
            if all(x <= q for x, q in zip(target, quotas)):
                result[target] = result.get(target, 0) + ca * cb
    return result


def file_terms(rank_eligibility, pawn_pairs, quotas, checkpoint=lambda: None):
    zero = (0,) * len(quotas)
    terms = []
    for own, enemy in pawn_pairs:
        checkpoint()
        if own == enemy or not (0 <= own < len(rank_eligibility) and 0 <= enemy < len(rank_eligibility)):
            raise ValueError('invalid physical Pawn pair')
        term = {zero: 1}
        for rank, groups in enumerate(rank_eligibility):
            if rank in (own, enemy):
                continue
            cell = {zero: 1}
            for group in groups:
                cell[tuple(int(index == group) for index in range(len(quotas)))] = 1
            term = multiply(term, cell, quotas, checkpoint)
        terms.append(term)
    return terms


def combine_files(terms, files, quotas, checkpoint=lambda: None):
    polynomial = {}
    for term in terms:
        for state, count in term.items():
            polynomial[state] = polynomial.get(state, 0) + count
    tables = [{(0,) * len(quotas): 1}]
    for _ in range(files):
        tables.append(multiply(tables[-1], polynomial, quotas, checkpoint))
    return polynomial, tables


def audit(budget=None):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen joint-count protocol changed')
    budget = budget or Budget(seconds=10)
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    expected = (lambda r: r <= 7, lambda r: r <= 6, lambda r: r >= 1, lambda r: r >= 2)
    masks = [compiled.support.empty_mobility[kind][owner] for owner, kind in GROUPS]
    if compiled.board_size != 9 or any(bool(mask[square]) != allowed(square // 9)
                                     for mask, allowed in zip(masks, expected) for square in range(81)):
        raise ValueError('compiled mobility differs from file-invariant declared scope')
    eligibility = tuple(tuple(g for g, mask in enumerate(masks) if mask[rank * 9]) for rank in range(9))
    pairs = [(a, b) for a in range(8) for b in range(1, 9) if a != b]
    quotas = (2, 2, 2, 2)
    terms = file_terms(eligibility, pairs, quotas, budget.checkpoint)
    polynomial, tables = combine_files(terms, 9, quotas, budget.checkpoint)
    joint = tables[-1][quotas]
    denominator = 57**9 * unrestricted_layouts(63)
    if not 0 < joint <= denominator or polynomial[(0, 0, 0, 0)] != 57:
        raise ValueError('invalid joint count')
    budget.checkpoint()
    return {'protocol_sha256': PROTOCOL_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'complete': True, 'joint_configurations': joint,
            'original_structural_configurations': denominator,
            'intrinsic_acceptance': str(Fraction(joint, denominator)),
            'file_pawn_pairs': len(pairs), 'file_table_states': len(polynomial),
            'maximum_table_states': max(map(len, tables)), 'files': 9,
            'elapsed_seconds': monotonic() - budget.started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result, indent=2))
