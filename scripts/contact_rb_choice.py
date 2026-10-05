"""Certified selection for the narrow contact0<B<R cone; no point coefficients."""
from generic_chess.core.terminal import TerminalStatus


def rb_contact_choice(children,game,*,owner,complete=False):
    """Caller binds the Chess contact theorem; complete four-piece native scope.

    This is not a generic vector scorer or proof of utility. ALL ongoing rows
    must contain only anchors and zero own/at most one each enemy native R/B.
    Shape plus the qualified contact cone gives identical selection throughout
    gamma(0,1) and the B interval, with terminal-first canonical ties.
    """
    if type(owner) is not int or owner not in (0,1) or not children:
        raise ValueError('nonempty table and explicit owner required')
    if any(not isinstance(k,str) or not k for k in children):
        raise ValueError('lossless canonical string IDs required')
    if complete is not True:
        return dict(complete=False,selected=None,reason='incomplete table')
    ranks={}
    for key,child in children.items():
        terminal=game.terminal(child)
        if terminal.is_terminal:
            if terminal.status is TerminalStatus.NO_CONTEST or getattr(terminal,'unresolved',False):
                return dict(complete=False,selected=None,reason='unqualified terminal',unresolved_choice=key)
            if terminal.winner not in (None,0,1):
                raise ValueError('invalid winner')
            category=2 if terminal.winner is None else 3 if terminal.winner==owner else 0
            ranks[key]=(category,0,0)
            continue
        pos=child.position;counts={'R':0,'B':0}
        if any(hand.total() for hand in pos.hands):
            raise ValueError('held modes outside scoped contact theorem')
        for p in pos.board:
            if p is None or p.current_type_id=='K':
                continue
            if (p.owner!=1-owner or p.base_type_id!=p.current_type_id
                    or p.current_type_id not in counts or p.promoted):
                raise ValueError('unqualified ordinary mode/origin/owner')
            counts[p.current_type_id]+=1
        if max(counts.values())>1 or not sum(counts.values()):
            raise ValueError('binary enemy R/B with positive remaining count required')
        ranks[key]=(1,-counts['R'],-counts['B'])
    best=max(ranks.values());selected=min(k for k in children if ranks[k]==best)
    return dict(complete=True,selected=selected,ranks=ranks,
                certificate='same selection for qualified0<B<R<1 contact family; common bound31')
