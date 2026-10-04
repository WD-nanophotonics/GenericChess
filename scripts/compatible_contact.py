"""Definite-occupancy source-only contact; no official game/valuation sampler."""
from dataclasses import dataclass
from fractions import Fraction as F
from scripts.public_task_intervals import integrate_public_action


@dataclass(frozen=True)
class SourceNode:
    base: str
    current: str
    square: int


@dataclass(frozen=True)
class ContactStep:
    event: tuple
    node: SourceNode
    completed: bool


def _world(node, *, area, owner, target, blockers):
    if type(area) is not int or area<=0 or type(owner) is not int or owner not in (0,1):
        raise ValueError('positive board area and explicit owner required')
    if (not isinstance(node,SourceNode) or type(node.base) is not str or not node.base
            or type(node.current) is not str or not node.current
            or type(node.square) is not int or not 0<=node.square<area
            or type(target) is not int or not 0<=target<area or target==node.square):
        raise ValueError('distinct source/target with explicit origin/current type required')
    if (any(type(s) is not int or not 0<=s<area for s in blockers)
            or any(label!='own' for label in blockers.values())
            or node.square in blockers or target in blockers):
        raise ValueError('fixed passive own blockers must be distinct from source/target')
    return {**blockers,node.square:'own',target:'enemy'}


def contact_steps(node, events, *, area, owner, target, blockers, goal_only=False, checkpoint=None,max_choices=128):
    """Exact for SUPPLIED intrinsic event grammar and definite virtual world.

    Caller authenticates compiled pattern coverage/exclusions and budget.
    Source origin persists across quiet moves/promotion; source square vacates.
    The designated removal is absorbing, not multiple reward for descriptions.
    goal_only enumerates possible last contact edges without materializing quiet
    successors; it cannot be used as a complete planning choice set.
    """
    if type(goal_only) is not bool:
        raise ValueError('explicit goal-only query flag required')
    if checkpoint is not None and not callable(checkpoint):
        raise ValueError('callable materialization checkpoint required')
    if type(max_choices) is not int or not 1<=max_choices<=128:
        raise ValueError('contact choice cap must be in1..128')
    board=_world(node,area=area,owner=owner,target=target,blockers=blockers)
    result={};matched_choices=0
    for key,cubes in events.items():
        if not isinstance(key,tuple) or len(key)!=7:
            raise ValueError('full physical event key required')
        actor,current,source,destination,label,removals,new_type=key
        if (type(actor) is not int or actor not in (0,1) or type(source) is not int
                or not 0<=source<area or type(current) is not str or not current):
            raise ValueError('explicit actor/current/source identity required')
        if (actor,current,source)!=(owner,node.current,node.square):
            continue
        if (type(destination) is not int or not 0<=destination<area or destination==source
                or label not in ('empty','enemy') or not isinstance(removals,tuple)
                or type(new_type) is not str or not new_type):
            raise ValueError('unsupported event destination/transition semantics')
        matched=False
        for cube in cubes:
            if any(type(s) is not int or not 0<=s<area or not labels
                   or any(x not in ('empty','own','enemy') for x in labels) for s,labels in cube):
                raise ValueError('definite occupancy cube required')
            if all(board.get(s,'empty') in labels for s,labels in cube):
                matched=True
        if not matched:
            continue
        if board.get(destination,'empty')!=label:
            raise ValueError('matched cube disagrees with physical target label')
        if removals:
            if (len(removals)!=1 or not isinstance(removals[0],tuple) or len(removals[0])!=2
                    or removals[0][0]!=target or removals[0][1] not in ('remove_from_game','capture_to_hand')):
                raise ValueError('only one designated target removal is supported')
            completed=True
        else:
            if label=='enemy':raise ValueError('enemy destination without physical removal')
            completed=False
        matched_choices+=1
        if matched_choices>max_choices:
            raise ValueError('matched contact choice cap exceeded')
        if goal_only and not completed:
            continue
        if checkpoint is not None:
            checkpoint()
        result[key]=ContactStep(key,SourceNode(node.base,new_type,destination),completed)
    return result


def discounted_contact_interval(gamma, *, excluded_through, witness_length=None, unreachable=False):
    """Distance proof frontier plus compatible witness, not a budget-as-zero.

    For0<gamma<1, proven tau>k gives upper gamma^(k+1); a path of length w
    gives lower gamma^w. Closed unreachable proof alone permits exact0.
    """
    if (type(gamma) is not int and not isinstance(gamma,F)) or not 0<gamma<1:
        raise ValueError('exact discount strictly between0 and1 required')
    if type(excluded_through) is not int or excluded_through<0 or type(unreachable) is not bool:
        raise ValueError('explicit distance frontier/closure required')
    if witness_length is not None and (type(witness_length) is not int or witness_length<=excluded_through):
        raise ValueError('witness must exceed the proven exclusion frontier')
    if unreachable and witness_length is not None:
        raise ValueError('unreachable proof conflicts with witness')
    if unreachable:return F(0),F(0)
    return (F(0) if witness_length is None else F(gamma)**witness_length,
            F(gamma)**(excluded_through+1))


def integrate_contact_intervals(weights,bounds):
    return integrate_public_action(weights,bounds)
