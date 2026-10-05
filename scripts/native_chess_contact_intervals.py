"""Research-only standardized contact intervals and complete-child certificates.

No Core changes, point estimates, source labels, model calls or search fallback.
Current-type origin tying is scoped to Western rights-disabled ordinary modes.
"""
from fractions import Fraction as F

from generic_chess.core.terminal import TerminalStatus
from scripts.material_interval_choice import certified_ongoing_material_choice
from scripts.material_leaf_choice import inventory_features

FINGERPRINT='7bc6cf3179f4eaea30b205576b9032dca47a16803e9cc8b3e29405cb1e820b35'
EMPTY_AUX=(((0,-1),0),((1,-1),0),((2,-1),None),((3,-1),0),((4,-1),0))
MODES=('P','N','B','R','Q')
TERMINAL_UNIT=('certificate','terminal_unit')
TOKEN_BOUND=30


def native_contact_intervals(duration):
    """Exact normalized envelopes for two predeclared laws or their safe hull."""
    if duration=='both':
        a=native_contact_intervals('geometric_half')
        b=native_contact_intervals('linear_mixture')
        return {k:(min(a[k][0],b[k][0]),max(a[k][1],b[k][1])) for k in a}
    if duration=='geometric_half':
        m=lambda t:F(1,2)**t
    elif duration=='linear_mixture':
        m=lambda t:F(2,(t+1)*(t+2))
    else:
        raise ValueError('use a predeclared duration: geometric_half, linear_mixture or both')
    total=249984
    r=(53760*m(1)+194432*m(2)+1792*m(3))/total
    q=(87696*m(1)+162048*m(2)+240*m(3))/total
    b=(33936*m(1)+85824*m(2))/total
    n=(20832*m(1)+66472*m(2)+94944*m(3))/total
    overlap={1:6596,2:770,3:770,4:770,5:770,6:1540,7:770}
    p=(6076*m(1)+16112*m(2)+sum((23870-overlap[k])*m(k+3)
                                for k in range(1,8)))/total
    raw={'Q':(q,q),'R':(r,r),'B':(b,b+3008*m(3)/total),
         'N':(n+(11200*m(61)+56536*m(62))/total,
              n+(11200*m(5)+56536*m(4))/total),
         'P':(p,(6076*m(1)+16112*m(2)+170844*m(3))/total)}
    # Failure invalidates the declared constructor, never fixes a mode/order.
    if not all(raw[x][0]>raw[y][1]>0 for x,y in zip(('Q','R','N','B'),('R','N','B','P'))):
        raise ValueError('qualified native ordering proof no longer holds')
    return {('board',tid):(lo/q,hi/q) for tid,(lo,hi) in raw.items()}


def _ongoing_features(position):
    if tuple(position.aux_state)!=EMPTY_AUX:
        raise ValueError('explicit zero rights and absent EP required')
    if any(hand.total() for hand in position.hands):
        raise ValueError('held modes unqualified')
    anchors=[0,0];ordinary=0
    for piece in position.board:
        if piece is None:
            continue
        if type(piece.owner) is not int or piece.owner not in (0,1):
            raise ValueError('invalid owner')
        tid=piece.current_type_id
        native=piece.base_type_id==tid and not piece.promoted
        pawn_origin=(piece.base_type_id=='P' and piece.promoted and tid in ('N','B','R','Q'))
        if not (native or pawn_origin):
            raise ValueError('unqualified origin/current mode')
        if tid=='K':
            if not native:
                raise ValueError('native anchors required')
            anchors[piece.owner]+=1
        elif tid in MODES:
            ordinary+=1
        else:
            raise ValueError('missing ordinary mode')
    if anchors!=[1,1] or ordinary>TOKEN_BOUND:
        raise ValueError('one native anchor per owner and <=30 ordinary tokens required')
    return inventory_features(position,{'K'})


def contact_interval_choice(children,game,*,owner,duration,complete=False):
    """Caller supplies an authoritative full child table, not coordinate moves."""
    if type(owner) is not int or owner not in (0,1) or not children:
        raise ValueError('nonempty child table and owner0/1 required')
    if any(not isinstance(k,str) or not k for k in children):
        raise ValueError('lossless canonical string IDs required')
    intervals=native_contact_intervals(duration)
    if complete is not True:
        return dict(complete=False,selected=None,reason='incomplete choice table')
    features={};intervals[TERMINAL_UNIT]=(F(1),F(1))
    for key,child in children.items():
        p=child.position
        if p.ruleset_fingerprint!=FINGERPRINT or p.board_shape.width!=8 or p.board_shape.height!=8:
            return dict(complete=False,selected=None,reason='unqualified Western rules/shape',unsupported_choice=key)
        t=game.terminal(child)
        if t.is_terminal:
            if getattr(t,'unresolved',False) or t.status not in (
                    TerminalStatus.CHECKMATE,TerminalStatus.STALEMATE,
                    TerminalStatus.MAX_PLY,TerminalStatus.REPETITION):
                return dict(complete=False,selected=None,reason='unqualified terminal/claim',unsupported_choice=key)
            if ((t.status is TerminalStatus.CHECKMATE and t.winner not in (0,1))
                    or (t.status is not TerminalStatus.CHECKMATE and t.winner is not None)):
                return dict(complete=False,selected=None,reason='unqualified Western terminal winner',unsupported_choice=key)
            features[key]={TERMINAL_UNIT:0 if t.winner is None else (31 if t.winner==0 else -31)}
        else:
            try:
                features[key]=_ongoing_features(p)
            except ValueError as error:
                return dict(complete=False,selected=None,reason=str(error),unsupported_choice=key)
    result=certified_ongoing_material_choice(features,intervals,owner=owner,complete=True)
    return dict(result,features=features,duration=duration,common_denominator=31,
                scope='research-only Western current-mode no-rights/EP interval candidate')
