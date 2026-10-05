"""Strict noncheck Standard Shogi20-mode approximate leaf interface, research only."""
from fractions import Fraction as F
import json
from pathlib import Path
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.terminal import TerminalStatus as T
from scripts.shogi_complete_board_intervals import board_intervals
from scripts.material_interval_choice import certified_ongoing_material_choice
from scripts.material_leaf_choice import inventory_features
from scripts.resource_mode_context import resource_ledger
FINGERPRINT='ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635'
TOKEN_BOUND=38
TERMINAL_UNIT=('certificate','terminal_unit')
HAND_REPORT=Path(__file__).resolve().parents[1]/'docs/research/data/shogi_random_deployment_20261005.json'


def shogi_contact_intervals(duration):
    board=board_intervals(duration,third=True)
    report=json.loads(HAND_REPORT.read_text(encoding='utf-8'))
    if not report['complete'] or not report['source_hashes_unchanged']:raise ValueError('complete hand evidence required')
    raw={('board',tid):pair for tid,pair in board.items()}
    if {r['type'] for r in report['rows']}!=set('PLNSGBR'):raise ValueError('complete native hand modes required')
    raw.update({('hand',r['type']):tuple(map(F,r['bounds'][duration])) for r in report['rows']})
    lo,hi=raw['board','TR']
    if lo!=hi or lo<=0 or len(raw)!=20 or any(not 0<a<=b<=lo for a,b in raw.values()):raise ValueError('exact common maximum proof fails')
    return {key:(a/lo,b/lo) for key,(a,b) in raw.items()}


def shogi_contact_choice(children,game,*,owner,duration,complete=False):
    if type(owner) is not int or owner not in (0,1) or not children:raise ValueError('nonempty table and owner0/1 required')
    if any(not isinstance(k,str) or not k for k in children):raise ValueError('lossless string IDs required')
    if duration=='both':
        results={law:shogi_contact_choice(children,game,owner=owner,duration=law,complete=complete)
                 for law in ('geometric_half','linear_mixture')}
        if not all(r['complete'] for r in results.values()):return dict(complete=False,selected=None,by_law=results,reason='unsupported whole table')
        picks={r['selected'] for r in results.values()}
        return dict(complete=True,selected=next(iter(picks)) if len(picks)==1 and None not in picks else None,
                    by_law=results,reason='separate-law shared choice; no outer hull',common_denominator=39)
    intervals=shogi_contact_intervals(duration);intervals[TERMINAL_UNIT]=(F(1),F(1))
    if complete is not True:return dict(complete=False,selected=None,reason='incomplete choice table')
    c=game.compiled
    if c.ruleset_fingerprint!=FINGERPRINT:return dict(complete=False,selected=None,reason='unqualified Standard Shogi rules')
    engine=semantic_engine_for(c);features={}
    for key,child in children.items():
        p=child.position
        try:
            if p.board_shape.width!=9 or p.board_shape.height!=9 or p.aux_state!=():raise ValueError('9x9 and explicit empty aux required')
            resource_ledger(c,p,'shogi')
            terminal=game.terminal(child)
            if terminal.is_terminal:
                if (getattr(terminal,'unresolved',False) or terminal.status not in (T.CHECKMATE,T.MAX_PLY)
                        or (terminal.status is T.CHECKMATE and (type(terminal.winner) is not int or terminal.winner not in (0,1)))
                        or (terminal.status is T.MAX_PLY and terminal.winner is not None)):
                    raise ValueError('unqualified terminal/claim')
                features[key]={TERMINAL_UNIT:0 if terminal.winner is None else (39 if terminal.winner==0 else -39)}
            else:
                if type(p.side_to_move) is not int or p.side_to_move not in (0,1):raise ValueError('valid current owner required')
                if engine.in_check(p,p.side_to_move):raise ValueError('checked leaf outside deployment scope')
                features[key]=inventory_features(p,{'K'})
        except ValueError as error:
            return dict(complete=False,selected=None,reason=str(error),unsupported_choice=key)
    result=certified_ongoing_material_choice(features,intervals,owner=owner,complete=True)
    return dict(result,features=features,duration=duration,common_denominator=39,
                scope='research-only full-stock noncheck Shogi board/hand virtual interval approximation')
