"""Exact supplied-dual choice certificates; caller owns semantic proof scope."""
from scripts.material_interval_choice import material_margin_interval
from scripts.coupled_linear_bounds import certified_lower


def coupled_material_choice(children,boxes,constraints,witnesses,*,owner,complete=False):
    if not children or type(owner) is not int or owner not in (0,1):raise ValueError('nonempty table and owner0/1 required')
    for key,features in children.items():
        if not isinstance(key,str) or not key:raise ValueError('canonical choice IDs required')
        material_margin_interval(features,features,boxes,owner=owner)
    if complete is not True:return dict(complete=False,selected=None,reason='incomplete table')
    for first in sorted(children):
        margins={}
        for second in sorted(children):
            if first==second:continue
            a,b=children[first],children[second]
            coefficients={key:(a.get(key,0)-b.get(key,0))*(1 if owner==0 else -1) for key in a.keys()|b.keys()}
            lower=certified_lower(coefficients,boxes,constraints,witnesses.get((first,second),{}))
            margins[second]=lower
            if lower<0 or (lower==0 and second<first):break
        else:return dict(complete=True,selected=first,margins=margins,reason='same canonical choice under supplied proved constraints')
    return dict(complete=True,selected=None,reason='supplied witnesses do not certify a choice')
