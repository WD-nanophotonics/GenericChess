"""Uniform exact physical joint draw; no corpus or game-task labels."""
import hashlib
import json
from pathlib import Path
import random
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_file_joint_count import combine_files, file_terms, multiply
from scripts.audit_reverse_placement_efficiency import GROUPS
from scripts.audit_secured_exchange_common_context import Budget

PROTOCOL = ROOT / 'docs/research/FILE_JOINT_UNRANK_PROTOCOL.md'
PROTOCOL_SHA = '53da16b150c3646d0d2b88c7c3baef79719c0de5a810a415a2d00796aef6ef41'


class JointSpace:
    def __init__(self, eligibility, pairs, files, quotas, checkpoint=lambda: None):
        self.eligibility = tuple(eligibility)
        self.pairs = tuple(pairs)
        self.files = files
        self.quotas = tuple(quotas)
        self.checkpoint = checkpoint
        self.terms = file_terms(eligibility, pairs, quotas, checkpoint)
        self.polynomial, self.tables = combine_files(self.terms, files, quotas, checkpoint)
        self.total = self.tables[-1].get(self.quotas, 0)

    def unrank_file(self, quota, rank):
        for pair, term in zip(self.pairs, self.terms):
            block = term.get(quota, 0)
            if rank < block:
                break
            rank -= block
        else:
            raise ValueError('file rank outside support')
        free = [r for r in range(len(self.eligibility)) if r not in pair]
        zero = (0,) * len(quota)
        suffix = [{zero: 1}]
        for r in reversed(free):
            cell = {zero: 1}
            for group in self.eligibility[r]:
                cell[tuple(int(g == group) for g in range(len(quota)))] = 1
            suffix.append(multiply(cell, suffix[-1], quota, self.checkpoint))
        remaining = quota
        placements = []
        for index, r in enumerate(free):
            for group in (-1, *self.eligibility[r]):
                next_quota = tuple(n - int(g == group) for g, n in enumerate(remaining))
                block = suffix[len(free) - index - 1].get(next_quota, 0)
                if rank < block:
                    remaining = next_quota
                    if group != -1:
                        placements.append((r, group))
                    break
                rank -= block
            else:
                raise ValueError('cell rank outside support')
        if rank or any(remaining):
            raise ValueError('incomplete file unrank')
        return pair, tuple(placements)

    def unrank(self, rank):
        if not isinstance(rank, int) or not 0 <= rank < self.total:
            raise ValueError('joint rank outside support')
        remaining = self.quotas
        result = []
        for file in range(self.files):
            self.checkpoint()
            for group_counts, count in sorted(self.polynomial.items()):
                rest = tuple(q - n for q, n in zip(remaining, group_counts))
                suffix_count = self.tables[self.files - file - 1].get(rest, 0)
                block = count * suffix_count
                if rank < block:
                    local_rank, rank = divmod(rank, suffix_count)
                    result.append(self.unrank_file(group_counts, local_rank))
                    remaining = rest
                    break
                rank -= block
            else:
                raise ValueError('joint block outside support')
        if rank or any(remaining):
            raise ValueError('incomplete joint unrank')
        return tuple(result)


def audit(budget=None):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen unranking protocol changed')
    budget = budget or Budget(seconds=10)
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    masks = [compiled.support.empty_mobility[kind][owner] for owner, kind in GROUPS]
    expected = (lambda r: r <= 7, lambda r: r <= 6, lambda r: r >= 1, lambda r: r >= 2)
    if compiled.board_size != 9 or any(bool(mask[s]) != allowed(s // 9)
                                     for mask, allowed in zip(masks, expected) for s in range(81)):
        raise ValueError('actual file-invariant mobility scope differs')
    eligibility = tuple(tuple(g for g, mask in enumerate(masks) if mask[rank * 9]) for rank in range(9))
    pairs = [(a, b) for a in range(8) for b in range(1, 9) if a != b]
    space = JointSpace(eligibility, pairs, 9, (2, 2, 2, 2), budget.checkpoint)
    seed = 202610040401
    rank = random.Random(seed).randrange(space.total)
    layout = space.unrank(rank)
    pieces = []
    for file, (pair, groups) in enumerate(layout):
        pieces.extend((owner, 'P', r * 9 + file) for owner, r in enumerate(pair))
        pieces.extend((*GROUPS[group], r * 9 + file) for r, group in groups)
    if len(pieces) != 26 or len({s for _, _, s in pieces}) != 26:
        raise ValueError('overlap or wrong total')
    for owner, kind in GROUPS:
        squares = [s for o, k, s in pieces if (o, k) == (owner, kind)]
        if len(squares) != 2 or any(not compiled.support.empty_mobility[kind][owner][s] for s in squares):
            raise ValueError('wrong restricted inventory or dead placement')
    for owner in (0, 1):
        pawns = [s for o, k, s in pieces if (o, k) == (owner, 'P')]
        if len(pawns) != 9 or {s % 9 for s in pawns} != set(range(9)) or any(
                not compiled.support.empty_mobility['P'][owner][s] for s in pawns):
            raise ValueError('wrong Pawn inventory, nifu or dead placement')
    budget.checkpoint()
    return {'protocol_sha256': PROTOCOL_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'count_program_sha256': hashlib.sha256((ROOT / 'scripts/audit_file_joint_count.py').read_bytes()).hexdigest(),
            'complete': True, 'seed': seed, 'rank': rank, 'joint_configurations': space.total,
            'physical_placements': sorted(pieces),
            'elapsed_seconds': monotonic() - budget.started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result, indent=2))
