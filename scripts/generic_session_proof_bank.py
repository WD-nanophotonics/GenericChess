"""Opt-in bounded process-local logical proof reuse, separate physical receipts.

Not a drop-in chooser/prover: BankQuery deliberately has no status/nodes fields.
A cache hit does NOT pay for work again and MUST NOT grant normal search more
budget in a comparison. A future player needs explicit separate phase caps.
Only node-completed/exhausted UNKNOWN and independently verified WIN are stored;
time/cancel/depth/unsupported/failed-verification outcomes never become entries.
No position-only key, disk cache, normal move/price cache or cross-agent state.
A hit returns HISTORICAL verification under the identical declared limits; an
adopting SessionStrategyCursor must still verify under its current allowance.
"""
from collections import OrderedDict
from dataclasses import dataclass
from time import perf_counter
from scripts.generic_win_proof import _Budget, _Interrupted, _same_state
from scripts.generic_session_win_proof import (
    SessionProofResult, replay_bound, verify_session_certificate)
from scripts.generic_session_win_proof_pn import prove_session_win_pn


@dataclass(frozen=True)
class BankQuery:
    logical_result: object
    hit: bool
    stored: bool
    actual_proof_nodes: int
    actual_verification_nodes: int
    seconds: float
    proof_seconds: float
    verification_seconds: float
    origin_reference_seconds: float
    verification: object | None
    key: tuple
    verification_scope: str = 'NONE'
    physical_proof_stats: tuple = ()


class SessionLogicalProofBank:
    def __init__(self, solver=prove_session_win_pn, *, capacity=256):
        if type(capacity) is not int or capacity < 1:
            raise ValueError('capacity must be positive integer')
        self._solver = solver
        self.capacity = capacity
        self._entries = OrderedDict()

    def query(self, session, *, target=None, max_nodes=4096, seconds=1.,
            max_depth=8, cancel=None, verification_max_nodes=65536,
            verification_seconds=1., _clock=perf_counter):
        target = session.state.position.side_to_move if target is None else target
        if type(target) is not int or target not in (0, 1): raise ValueError('invalid target')
        if type(max_depth) is not int or not 0 <= max_depth <= 128: raise ValueError('invalid depth')
        b = _Budget(max_nodes, seconds, cancel, _clock)
        # Validate independent verification limits even on a cache hit.
        _Budget(verification_max_nodes, verification_seconds, cancel, _clock)
        root, record, terminal = session.state, session.to_record(), session.result
        key = (session.compiled.ruleset_fingerprint, repr(record), repr(root),
            repr(terminal), target, max_nodes, seconds, max_depth,
            verification_max_nodes, verification_seconds)
        result = None
        proof_nodes = verifier_nodes = 0
        proof_time = verifier_time = 0.
        verification = None
        hit = stored = False
        origin_time = 0.
        physical_stats = ()
        try:
            b.poll(); replay_bound(session); b.poll()
            if key in self._entries:
                result, verification = self._entries[key]
                self._entries.move_to_end(key)
                origin_time = result.seconds
                hit = True
                physical_stats = tuple((n, 0) for n in (
                    'frontiers','transitions','iterations','peak_depth',
                    'eager_board_successors','claims_assessed') if hasattr(result,n))
                b.poll()
            else:
                # Admission is part of this physical query's wall allowance.
                result = self._solver(session, target=target, max_nodes=max_nodes,
                    seconds=max(0., seconds-b.elapsed()), max_depth=max_depth,
                    cancel=cancel, _clock=_clock)
                proof_nodes, proof_time = result.nodes, result.seconds
                physical_stats = tuple((n, getattr(result,n)) for n in (
                    'frontiers','transitions','iterations','peak_depth',
                    'eager_board_successors','claims_assessed') if hasattr(result,n))
                origin_time = result.seconds
                b.poll()
                eligible = result.status == 'UNKNOWN' and result.reason in (
                    'node_budget', 'no_forced_win_in_exhausted_tree')
                if result.status == 'PROVEN_WIN' and getattr(result.certificate, 'target', None) != target:
                    result = SessionProofResult('UNKNOWN', None,
                        'certificate_target_mismatch', proof_nodes, proof_time, 0)
                if result.status == 'PROVEN_WIN':
                    # Verification has its own declared allowance. The proof
                    # query wall deadline cannot silently prohibit its check.
                    verification = verify_session_certificate(session,
                        result.certificate, max_nodes=verification_max_nodes,
                        seconds=verification_seconds, cancel=cancel, _clock=_clock)
                    verifier_nodes = verification['nodes']
                    verifier_time = verification['seconds']
                    eligible = verification['verified']
                if cancel is not None and cancel():
                    b.reason = 'cancelled'; raise _Interrupted('cancelled')
                if eligible:
                    self._entries[key] = (result, None if verification is None else dict(verification))
                    self._entries.move_to_end(key)
                    while len(self._entries) > self.capacity:
                        self._entries.popitem(last=False)
                    stored = True
            if cancel is not None and cancel():
                b.reason = 'cancelled'; raise _Interrupted('cancelled')
        except _Interrupted:
            result = SessionProofResult('UNKNOWN', None, b.reason,
                proof_nodes, proof_time, 0)
        except (NotImplementedError, ValueError):
            result = SessionProofResult('UNKNOWN', None,
                'unsupported_or_unreplayable_session', proof_nodes, proof_time, 0)
        finally:
            assert _same_state(session.state, root) and _same_state(session.to_record(), record) and session.result == terminal
        return BankQuery(result, hit, stored, proof_nodes, verifier_nodes,
            b.elapsed(), proof_time, verifier_time, origin_time, None if verification is None else dict(verification), key,
            'NONE' if verification is None else 'HISTORICAL_SAME_LIMITS' if hit else 'THIS_QUERY', physical_stats)
