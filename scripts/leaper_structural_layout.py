"""Geometry-only opening recipe for prospective ordinary Leap rules.

Not a replacement for any frozen panel. Does not compile, run Core/Player, sample
seeds or inspect outcomes. Returns literal symmetric cells plus a complete
geometry rejection ledger. Caller must later freeze the COMPLETE new ordinary
RuleSet/history/conditions and independently validate its executable semantics.
"""
from itertools import product

KING=frozenset((x,y) for x in (-1,0,1) for y in (-1,0,1) if (x,y)!=(0,0))

def layout(piece_types,n=8,copies=2,*,parity_only=False,scan="row"):
    if scan not in {"row","column"}:raise ValueError("fixed row or column scan required")
    if n!=8 or copies!=2:return {'status':'UNSUPPORTED','reason':'fixed prototype n8/two copies per nonanchor'}
    if not piece_types or len(piece_types)>4:return {'status':'UNSUPPORTED','reason':'at most one anchor and three nonanchors'}
    parsed={};anchors=[]
    for p in piece_types:
        tid=p['type_id']
        if tid in parsed:return {'status':'UNSUPPORTED','reason':'duplicate actor type'}
        if any(a.get('kind')!='leap' for a in p['movement_atoms']):return {'status':'UNSUPPORTED','reason':'nonLeap metadata'}
        offsets=frozenset(tuple(a['offset']) for a in p['movement_atoms']);parsed[tid]=offsets
        if p['is_anchor']:
            anchors.append(tid)
            if offsets!=KING:return {'status':'UNSUPPORTED','reason':'anchor geometry not eight neighbors'}
        elif not offsets or (parity_only and len({(x+y)&1 for x,y in offsets})!=1):return {'status':'UNSUPPORTED','reason':'nonanchor parity not homogeneous'}
    if len(anchors)!=1:return {'status':'UNSUPPORTED','reason':'exactly one anchor type'}
    k=anchors[0];kings={0:(0,3),1:(7,4)}
    # Four cells: two checkerboard colors, exact rotation under owner swap.
    reserve={0:{(0,2),(0,4),(1,2),(1,4)},1:{(7,5),(7,3),(6,5),(6,3)}}
    blocked=set(kings.values())|reserve[0]|reserve[1];taken=set(kings.values());placements=[{'owner':o,'type':k,'square':list(sq)} for o,sq in kings.items()];ledger=[]
    for tid in sorted(t for t in parsed if t!=k):
        for copy_index in range(copies):
            chosen=None;rejections=[]
            for y,x in product(range(n),range(n)):
                sq=(x,y) if scan=="row" else (y,x);x,y=sq;mirror=(7-x,7-y)
                if sq==mirror or sq in blocked or mirror in blocked or sq in taken or mirror in taken:rejections.append({'square':list(sq),'reason':'reserved/occupied'});continue
                # Legacy owner-relative frame rotates offsets for owner1.
                a0={(x+dx,y+dy) for dx,dy in parsed[tid]};a1={(mirror[0]-dx,mirror[1]-dy) for dx,dy in parsed[tid]}
                if a0 & (reserve[1]|{kings[1]}) or a1 & (reserve[0]|{kings[0]}):rejections.append({'square':list(sq),'reason':'opponent royal/reserved target geometrically attacked'});continue
                chosen=(sq,mirror);break
            ledger.append({'type':tid,'copy':copy_index,'rejections':rejections,'selected':chosen})
            if chosen is None:return {'status':'NO_LAYOUT','placements':placements,'ledger':ledger,'reason':'deterministic fixed order infeasible;no random or outcome retry'}
            for owner,sq in enumerate(chosen):placements.append({'owner':owner,'type':tid,'square':list(sq)});taken.add(sq)
    return {'status':'GEOMETRY_LAYOUT_ONLY','board':n,'scan':scan,'placements':placements,'reserved':{str(o):sorted(reserve[o]) for o in reserve},'ledger':ledger,'claim':'Prospective ordinary all-Leap domain;parity specialcase optional;not complete typedRuleSet/Core admission/holdout/quality. No frozen-panel replacement is dispatched.'}
