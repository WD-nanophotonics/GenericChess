"""Actual Shogi Q integration using exact restricted joint unranking."""
from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from random import Random
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_actual_inventory_sampling import pawn_pairs, rejection_reason, validate_structural
from scripts.audit_exchange_custody import synthetic_state
from scripts.audit_file_joint_unrank import GROUPS, JointSpace
from scripts.audit_post_capture_scope import state_evidence
from scripts.audit_secured_exchange_common_context import Budget

PROTOCOL = ROOT / 'docs/research/JOINT_ACTUAL_FRAME_PROTOCOL.md'
PROTOCOL_SHA = '54ddf7d00f4be464edadc7d38fc572c3856c61185b3dec56355b5f138f9a24bc'


def scope(compiled, position):
    tokens = [p for p in position.board if p]
    expected_counts = Counter({(owner, kind): count for owner in (0, 1)
                               for kind, count in [('P', 9), ('L', 2), ('N', 2), ('B', 1),
                                                   ('G', 2), ('K', 1), ('R', 1), ('S', 2)]})
    if compiled.board_size != 9 or Counter((p.owner, p.current_type_id) for p in tokens) != expected_counts or any(
            p.promoted or p.base_type_id != p.current_type_id for p in tokens):
        raise ValueError('declared actual unpromoted initial inventory required')
    masks = [compiled.support.empty_mobility[kind][owner] for owner, kind in GROUPS]
    expected = (lambda r: r <= 7, lambda r: r <= 6, lambda r: r >= 1, lambda r: r >= 2)
    if any(bool(mask[s]) != allowed(s // 9) for mask, allowed in zip(masks, expected) for s in range(81)):
        raise ValueError('restricted mobility scope changed')
    for owner in (0, 1):
        if any(bool(compiled.support.empty_mobility['P'][owner][s]) != (s // 9 != (8 if owner == 0 else 0))
               for s in range(81)):
            raise ValueError('Pawn mobility scope changed')
    others = [p for p in tokens if p.current_type_id not in ('P', 'L', 'N')]
    if any(not all(compiled.support.empty_mobility[p.current_type_id][p.owner]) for p in others):
        raise ValueError('unrestricted mobility scope changed')
    return masks, others


class ShogiJointSampler:
    def __init__(self, compiled, budget):
        self.compiled = compiled
        self.budget = budget
        self.template = initial_state(compiled).position
        masks, self.others = scope(compiled, self.template)
        eligibility = tuple(tuple(g for g, mask in enumerate(masks) if mask[rank * 9]) for rank in range(9))
        self.space = JointSpace(eligibility, pawn_pairs(), 9, (2, 2, 2, 2), budget.checkpoint)

    def sample(self, rng):
        self.budget.checkpoint()
        layout = self.space.unrank(rng.randrange(self.space.total))
        board = [None] * 81
        for file, (pair, groups) in enumerate(layout):
            for owner, rank in enumerate(pair):
                board[rank * 9 + file] = Piece(owner, 'P', 'P')
            for rank, group in groups:
                owner, kind = GROUPS[group]
                board[rank * 9 + file] = Piece(owner, kind, kind)
        free = [s for s, p in enumerate(board) if p is None]
        for square, piece in zip(rng.sample(free, len(self.others)), self.others):
            board[square] = piece
        position = replace(self.template, board=tuple(board), hands=(Hands.empty(), Hands.empty()), side_to_move=0)
        validate_structural(self.compiled, position, 'shogi')
        self.budget.checkpoint()
        return position


def audit(budget=None, proposal_limit=128):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen joint actual-frame protocol changed')
    if not 1 <= proposal_limit <= 128:
        raise ValueError('at most 128 joint proposals')
    budget = budget or Budget(seconds=10)
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    sampler = ShogiJointSampler(compiled, budget)
    rng = Random(202610040402)
    rejected = Counter(); selected = None
    for attempt in range(1, proposal_limit + 1):
        position = sampler.sample(rng)
        reason = rejection_reason(compiled, position, 'shogi', budget)
        if reason == 'dead_nonpawn_placement':
            raise ValueError('joint sampler emitted intrinsic dead placement')
        if reason:
            rejected[reason] += 1
            continue
        selected = state_evidence(synthetic_state(compiled, position), compiled)
        break
    budget.checkpoint()
    return {'protocol_sha256': PROTOCOL_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'unrank_program_sha256': hashlib.sha256((ROOT / 'scripts/audit_file_joint_unrank.py').read_bytes()).hexdigest(),
            'complete': selected is not None, 'seed': 202610040402, 'proposals': attempt,
            'rejected': dict(rejected), 'state': selected,
            'elapsed_seconds': monotonic() - budget.started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'state'}, indent=2))
