"""Opt-in proof scheduling from one complete finite-inventory absence census.

The evidence has a deliberately exact ruleset fingerprint. Unsupported games
always delegate to the original complete-choice prover. A hit returns UNKNOWN,
never DRAW, a winning certificate or an executable action. The caller's normal
search and actual Session adjudication remain authoritative. No product default.
"""
from collections import Counter
from dataclasses import replace
from pathlib import Path
from time import perf_counter
import hashlib,json
from generic_chess.session.result import SessionStatus
from scripts.generic_win_proof import _Budget,_Interrupted
from scripts.generic_session_win_proof import SessionProofResult,replay_bound
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn

class InventoryNoWinFilter:
    def __init__(self,census_folder,coverage_file,*,solver=prove_session_win_batch_pn):
        folder=Path(census_folder);census=json.loads((folder/'result.json').read_text());coverage=json.loads(Path(coverage_file).read_text())
        if census['status']!='COMPLETE' or coverage['status']!='PASS_COMPLETE_INPUT_COVERAGE_AND_ORIGINAL_CORE_EDGE_CENSUS':
            raise ValueError('complete independently covered census required')
        raw=(folder/'states.jsonl').read_bytes();canonical=b'\n'.join(raw.splitlines())+b'\n'
        if hashlib.sha256(canonical).hexdigest()!=census['records_sha'] or coverage['records_sha']!=census['records_sha']:
            raise ValueError('census records digest mismatch')
        plan=json.loads((folder/'plan.json').read_text())
        if hashlib.sha256(Path(plan['rules']).read_bytes()).hexdigest()!=census['rules_sha']:
            raise ValueError('census rule source mismatch')
        # The companion coverage explicitly corrects the preserved arithmetic
        # metadata error; it does not alter any original Core record/edge.
        rows=[json.loads(line) for line in raw.splitlines()];counts=Counter(r['inventory'] for r in rows)
        if dict(counts)!=coverage['admissible_by_inventory'] or sum(len(r['actions']) for r in rows)!=coverage['actual_legal_edges']:
            raise ValueError('census input or edge coverage mismatch')
        modes=set(coverage['no_win_inventories']);patterns=set()
        for row in rows:
            if row['inventory'] not in modes:continue
            if row['winner'] is not None:raise ValueError('winning terminal contradicts absence')
            pattern=Counter((int(piece.islower()),piece.upper()) for piece in row['board'][:-1] if piece!='.')
            patterns.add(tuple(sorted(pattern.items())))
        if not patterns:raise ValueError('no qualified absent-win inventory')
        self.fingerprint=census['ruleset_fingerprint'];self.patterns=frozenset(patterns);self.solver=solver
        self.records_sha=census['records_sha']

    def eligible(self,session):
        if session.compiled.ruleset_fingerprint!=self.fingerprint or session.result.status is not SessionStatus.ONGOING:return False
        position=session.state.position
        if position.aux_state or any(hand.total() for hand in position.hands):return False
        pieces=[piece for piece in position.board if piece is not None]
        if any(piece.promoted or piece.base_type_id!=piece.current_type_id for piece in pieces):return False
        pattern=tuple(sorted(Counter((piece.owner,piece.current_type_id) for piece in pieces).items()))
        return pattern in self.patterns

    def __call__(self,session,*,target=None,max_nodes=4096,seconds=1.,max_depth=8,cancel=None,_clock=perf_counter):
        target=session.state.position.side_to_move if target is None else target
        if type(target) is not int or target not in (0,1):raise ValueError('invalid target')
        if type(max_depth) is not int or not 0<=max_depth<=128:raise ValueError('invalid depth')
        b=_Budget(max_nodes,seconds,cancel,_clock)
        try:
            b.poll()
            if self.eligible(session):
                replay_bound(session);b.poll()
                return SessionProofResult('UNKNOWN',None,'certified_inventory_no_win',0,b.elapsed(),0)
            result=self.solver(session,target=target,max_nodes=max_nodes,seconds=max(0.,seconds-b.elapsed()),max_depth=max_depth,cancel=cancel,_clock=_clock)
            return replace(result,seconds=b.elapsed())
        except _Interrupted:return SessionProofResult('UNKNOWN',None,b.reason,0,b.elapsed(),0)
