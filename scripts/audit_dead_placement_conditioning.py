"""Exact completion counts; no random redraw or game-value computation."""
from fractions import Fraction
import hashlib
import json
from math import comb
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / 'docs/research/DEAD_PLACEMENT_CONDITIONING_PROTOCOL.md'
PROTOCOL_SHA = '9d09006c9d65f851661c16a4a6a60aa05aa50796107a9ae1990fe559fe2fab62'


def completion_count(eligible_cells, quotas, checkpoint=lambda: None):
    """Polynomial coefficient; each physical cell is empty or holds one group."""
    zero = (0,) * len(quotas); target = tuple(quotas); counts = {zero: 1}
    for eligible in eligible_cells:
        checkpoint(); updated = dict(counts)
        for state, count in counts.items():
            for group in eligible:
                if state[group] < target[group]:
                    next_state = tuple(value + (index == group) for index, value in enumerate(state))
                    updated[next_state] = updated.get(next_state, 0) + count
        counts = updated
    return counts.get(target, 0)


def audit():
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen dead-placement protocol changed')
    started = monotonic()
    def checkpoint():
        if monotonic() - started > 10:
            raise TimeoutError('exact completion count time cap')
    paths = [ROOT / 'docs/research/data' / name for name in
             ('physical_placement_sampling_20261003.json', 'physical_exchange_support_20261003.json')]
    physical, support = [json.loads(p.read_text()) for p in paths]
    boards = [('original', physical['games']['shogi']['physical_board'])] + [
        (f"support_proposal_{row['proposal']}", row['physical_board']) for row in support['roots'] if row['game'] == 'shogi']
    if len(boards) != 6:
        raise ValueError('frozen six Shogi frames required')
    rows = []
    for name, board in boards:
        checkpoint()
        pawn_cells = {index for index, piece in enumerate(board) if piece and piece[2] == 'P'}
        if len(board) != 81 or len(pawn_cells) != 18 or 3 * 9 + 3 not in pawn_cells:
            raise ValueError('invalid frozen Pawn frame')
        eligible = []
        for cell in range(81):
            if cell not in pawn_cells:
                rank = cell // 9
                eligible.append(tuple(group for group, allowed in enumerate(
                    (rank <= 7, rank <= 6, rank >= 1, rank >= 2)) if allowed))
        valid = completion_count(eligible, (2, 2, 2, 2), checkpoint)
        denominator = comb(63, 2) * comb(61, 2) * comb(59, 2) * comb(57, 2)
        rows.append({'frame': name, 'pawn_cells': sorted(pawn_cells),
                     'valid_restricted_completions': valid,
                     'unrestricted_completions': denominator,
                     'nondead_probability': str(Fraction(valid, denominator))})
    return {'protocol_sha256': PROTOCOL_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'input_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            'complete': True, 'rows': rows,
            'varying_completion_counts': len({row['valid_restricted_completions'] for row in rows}) > 1,
            'elapsed_seconds': monotonic() - started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
