"""Explicit fresh-root bridge to replayable sessions, never a history importer.

This research helper changes the rules fingerprint by adding a named initial
setup. It accepts ONLY a state exactly equal to a fresh state under that setup,
after validating and rebinding only fresh-root provenance keys. Existing history,
hands/aux rights or side-to-move that setup cannot express are rejected.
No private GameSession fields are written; callers retain the original rules.
"""
from dataclasses import replace
from generic_chess.rules.schema import RuleInitialSetupOption
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.position import HistoryRecord
from generic_chess.core.terminal import terminal_result
from scripts.generic_win_proof import _same_state


def fresh_setup_session(ruleset,state,*,setup_key):
    if not isinstance(setup_key,str) or not setup_key:
        raise ValueError('named setup key required')
    original=compile_ruleset_for_execution(ruleset)
    if state.position.ruleset_fingerprint!=original.ruleset_fingerprint:
        raise ValueError('source rules/state fingerprint mismatch')
    key=repetition_identity_key(state.position,original)
    if (type(state.ply_count) is not int or state.ply_count!=0
        or not _same_state(state.repetition_counts,((key,1),))
        or not _same_state(state.history,(HistoryRecord(key,-1,'',False),))
        or not _same_state(state.terminal_status,terminal_result(state,original))):
        raise ValueError('state is not expressible as an exact fresh named setup; existing history is never reset')
    if state.position.side_to_move!=0:
        raise ValueError('state is not expressible as an exact fresh named setup; setup schema has initial side0 only')
    if any(option.setup_key==setup_key for option in ruleset.initial_setup_options):
        raise ValueError('setup key already exists; do not overwrite original setup')
    width=state.position.board_shape.width
    height=state.position.board_shape.height
    board=state.position.board
    rows=tuple(tuple(board[y*width:(y+1)*width]) for y in range(height))
    extended=replace(ruleset,initial_setup_options=ruleset.initial_setup_options+(RuleInitialSetupOption(setup_key,rows),))
    compiled=compile_ruleset_for_execution(extended)
    session=GameSession(compiled,setup_key)
    # Identity includes the rules fingerprint. Only after exact fresh-history
    # admission may its single initial key be recomputed in the new definition.
    # No played history or repetition count can pass the admission above.
    position=replace(state.position,ruleset_fingerprint=compiled.ruleset_fingerprint)
    new_key=repetition_identity_key(position,compiled)
    expected=replace(state,position=position,repetition_counts=((new_key,1),),
                     history=(HistoryRecord(new_key,-1,'',False),))
    if not _same_state(session.state,expected):
        raise ValueError('state is not expressible as an exact fresh named setup; history/turn/rights retained, not reset')
    record=session.to_record()
    if not _same_state(GameSession.replay(compiled,record).state,session.state):
        raise ValueError('named setup record does not exactly replay')
    return extended,session
