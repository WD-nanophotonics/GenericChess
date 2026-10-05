"""Qualified declared dead/live support families and independent promotion oracle."""
from collections import deque
from dataclasses import replace
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.schema import RuleReplaceSelector
from scripts.promotable_micro_qualified import qualified_build
from scripts.audit_promotable_cube_micro import coordinate_steps as raw_steps
def build(*args,live=False,**kwargs):
    rules=qualified_build(*args,**kwargs)
    if not live:return rules
    promoted=rules.piece_types[1].type_id
    types=tuple(replace(p,movement_atoms=tuple(LeapAtom(x) for x in ((1,0),(-1,0),(0,1),(0,-1)))) if p.type_id==promoted else p for p in rules.piece_types)
    actions=tuple(replace(a,composition='replace_legacy',replace_selector=RuleReplaceSelector((promoted,),'board',a.target_relation,geometry_kind='leap',replace_all_matching=True)) if a.type_ids==(promoted,) else a for a in rules.semantic_actions)
    return replace(rules,piece_types=types,semantic_actions=actions)
def steps(source,current,owner,*,live):
    if live or current==1:yield from raw_steps(source,current,owner);return
    r=source//3+(1 if owner==0 else -1)
    if 0<=r<3 and r!=(2 if owner==0 else 0):yield source%3+3*r,0
def distance(source,target,blocker,current,owner,*,live):
    todo=deque([(source,current,0)]);seen={(source,current)}
    while todo:
        here,mode,cost=todo.popleft()
        for dest,result in steps(here,mode,owner,live=live):
            if dest==target:return cost+1
            if dest==blocker or (dest,result) in seen:continue
            seen.add((dest,result));todo.append((dest,result,cost+1))
    return 0
