"""Explicit checked-ongoing hypothesis, never a silent strict-scope fallback."""
from fractions import Fraction as F
from generic_chess.core.position import GameState
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.terminal import TerminalStatus as T
from scripts.shogi_contact_interval_choice import FINGERPRINT,TERMINAL_UNIT
from scripts.shogi_exact_twenty_family import exact_twenty_intervals
from scripts.material_leaf_choice import inventory_features
from scripts.material_interval_choice import certified_ongoing_material_choice
from scripts.resource_mode_context import resource_ledger

SCOPE='checked_ongoing_static'
def checked_ongoing_choice(children,game,*,owner,duration,complete=False,approximation_scope=None):
    if approximation_scope!=SCOPE:return dict(complete=False,selected=None,reason='explicit checked-ongoing approximation scope required')
    if type(owner) is not int or owner not in (0,1) or not children:raise ValueError('nonempty choice table and owner0/1 required')
    if any(not isinstance(k,str) or not k for k in children):raise ValueError('lossless choice identities required')
    if complete is not True:return dict(complete=False,selected=None,reason='incomplete choice table')
    if duration=='both':
        results={law:checked_ongoing_choice(children,game,owner=owner,duration=law,complete=True,approximation_scope=SCOPE) for law in ('geometric_half','linear_mixture')}
        if not all(row['complete'] for row in results.values()):return dict(complete=False,selected=None,by_law=results)
        picks={row['selected'] for row in results.values()}
        return dict(complete=True,selected=next(iter(picks)) if len(picks)==1 and None not in picks else None,by_law=results,scope=SCOPE)
    weights=exact_twenty_intervals(duration);weights[TERMINAL_UNIT]=(F(1),F(1))
    c=game.compiled
    if c.ruleset_fingerprint!=FINGERPRINT:return dict(complete=False,selected=None,reason='unqualified Standard Shogi rules')
    engine=semantic_engine_for(c);features={};checked=[]
    for key,child in children.items():
        try:
            if not isinstance(child,GameState):raise ValueError('full public GameState required; claims unsupported')
            p=child.position
            if p.board_shape.width!=9 or p.board_shape.height!=9 or p.aux_state!=():raise ValueError('9x9 and empty aux required')
            resource_ledger(c,p,'shogi');terminal=game.terminal(child)
            if terminal.is_terminal:
                if (getattr(terminal,'unresolved',False) or terminal.status not in (T.CHECKMATE,T.MAX_PLY)
                    or terminal.status is T.CHECKMATE and (type(terminal.winner) is not int or terminal.winner not in (0,1))
                    or terminal.status is T.MAX_PLY and terminal.winner is not None):raise ValueError('unqualified terminal/claim')
                features[key]={TERMINAL_UNIT:0 if terminal.winner is None else 39 if terminal.winner==0 else -39}
            else:
                if type(p.side_to_move) is not int or p.side_to_move not in (0,1):raise ValueError('valid current owner required')
                if engine.in_check(p,p.side_to_move):checked.append(key)
                features[key]=inventory_features(p,{'K'})
        except ValueError as error:return dict(complete=False,selected=None,reason=str(error),unsupported_choice=key)
    result=certified_ongoing_material_choice(features,weights,owner=owner,complete=True)
    return dict(result,features=features,checked_ongoing_choices=checked,duration=duration,common_denominator=39,
       scope=SCOPE,assumption='static material applied even in check; no check-evasion/survival/game-value calibration')
