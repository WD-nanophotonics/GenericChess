"""Frozen multi-horizon DEV scheduling; never reinterpret a trajectory prefix."""
from scripts.generic_proof_roles import roles,role_order


def horizon_settings(plan):
    hs=plan.get('horizons',[plan['H']]);modes=plan.get('proof_modes',[False,True])
    if not hs or len(set(hs))!=len(hs) or any(type(h) is not int or not 1<=h<=256 for h in hs):
        raise ValueError('unique positive integer horizons required')
    if not modes or len(set(modes))!=len(modes) or any(type(q) is not bool for q in modes):
        raise ValueError('unique boolean proof modes required')
    if len(hs)>1 and (plan.get('study_kind')=='LEARN' or any(f['phase']!='DEV' for f in plan['families'])):
        raise ValueError('multi-horizon assay requires frozen prices and DEV-only roots')
    return hs,modes


def dev_cases(plan,selected):
    hs,modes=horizon_settings(plan);base=plan.get('baseline_index',0)
    if 'horizons' not in plan and 'proof_modes' not in plan:
        # Preserve the legacy paid order exactly for existing single-H studies.
        for f in plan['families']:
            if f['phase']!='DEV':continue
            cells=[(False,base),(True,base)]
            if selected!=base:cells += [(False,selected),(True,selected)]
            if f['family']%2:cells.reverse()
            for enabled,index in cells:
                for color in (0,1):
                    for op in plan['opponents']:
                        for role in role_order(plan,f['family'],color):
                            yield f,enabled,index,color,op,role,plan['H']
        return
    for f in plan['families']:
        if f['phase']!='DEV':continue
        for color in (0,1):
            for op in plan['opponents']:
                for role in role_order(plan,f['family'],color):
                    reverse=(f['family']+color+roles(plan).index(role))%2
                    order=list(hs)
                    if reverse:order.reverse()
                    for h in order:
                        cells=[(q,i) for q in modes for i in dict.fromkeys([base,selected])]
                        if reverse:cells.reverse()
                        for enabled,index in cells:yield f,enabled,index,color,op,role,h
