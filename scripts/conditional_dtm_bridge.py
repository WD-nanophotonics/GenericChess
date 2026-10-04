"""Pure conditional horizon arithmetic; no table files, probes or labels."""
from generic_chess.core.terminal import TerminalStatus

UNKNOWN = (-1, 1)
PREMISES = frozenset(('same_move_goal_semantics', 'exact_minimax_dtm',
                     'mate_priority_at_horizon', 'other_history_draws_excluded',
                     'source_and_state_conversion_verified'))


def dtm_horizon_interval(*, side, ply, max_ply, repetition_limit,
                         max_repetition_count, wdl_stm, signed_dtm,
                         premises, distance_kind='DTM'):
    """Conditional owner-zero result for an ONGOING root.

    True premise flags encode assumptions, not verification of external sources.
    Missing/false flags yield unknown. A production certificate adapter still
    needs source/checksum, full state association and move/history conversion.
    DTM is signed half-moves from side-to-move; DTZ is never accepted as DTM.
    """
    if (type(side) is not int or side not in (0, 1)
            or any(type(x) is not int for x in (ply, max_ply, repetition_limit, max_repetition_count))
            or ply < 0 or max_ply <= ply or repetition_limit < 2 or max_repetition_count < 1):
        raise ValueError('valid ongoing root orientation/horizon/history required')
    horizon = max_ply-ply
    if distance_kind != 'DTM' or premises.keys() != PREMISES or any(v is not True for v in premises.values()):
        return {'interval': UNKNOWN, 'reason': 'unverified DTM/semantic premises', 'horizon': horizon}
    if max_repetition_count+horizon >= repetition_limit:
        return {'interval': UNKNOWN, 'reason': 'earlier repetition not excluded', 'horizon': horizon}
    if type(wdl_stm) is not int or wdl_stm not in (-1, 0, 1) or type(signed_dtm) is not int:
        return {'interval': UNKNOWN, 'reason': 'missing/invalid certificate', 'horizon': horizon}
    if ((wdl_stm == 0 and signed_dtm != 0)
            or wdl_stm and (signed_dtm == 0 or (1 if signed_dtm > 0 else -1) != wdl_stm)):
        return {'interval': UNKNOWN, 'reason': 'ambiguous/inconsistent ongoing DTM', 'horizon': horizon}
    if wdl_stm == 0 or abs(signed_dtm) > horizon:
        value = 0
    else:
        value = wdl_stm*(1 if side == 0 else -1)
    return {'interval': (value, value), 'reason': 'conditional exact finite horizon', 'horizon': horizon}


def terminal_first_interval(state, game, certificate_arguments, *, censored_statuses=()):
    """Fresh authoritative terminal interface outranks any ongoing certificate.

    PublicGame.terminal also rejects a stale cached local terminal. An unresolved
    claim/censored adjudication stays unknown instead of consulting a DTM label.
    """
    terminal = game.terminal(state)
    if terminal.is_terminal:
        if (terminal.status is TerminalStatus.NO_CONTEST or terminal.status in censored_statuses
                or getattr(terminal, 'unresolved', False)):
            return {'interval': UNKNOWN, 'reason': 'unqualified local terminal'}
        if terminal.winner is not None and (type(terminal.winner) is not int or terminal.winner not in (0, 1)):
            raise ValueError('valid terminal winner required')
        value = 0 if terminal.winner is None else 1 if terminal.winner == 0 else -1
        return {'interval': (value, value), 'reason': 'authoritative local terminal'}
    return dtm_horizon_interval(**certificate_arguments)
