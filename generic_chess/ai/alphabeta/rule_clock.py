"""Conservative opt-in finite-clock bound for simple pure-Leaper searches.

This caps requested main depth, never the record/history or live work budgets.
Admission excludes policies which may keep the game ongoing at max_ply.
"""
from dataclasses import replace
from ...core.movement import LeapAtom

def capped_pure_leaper_limits(state, compiled, limits):
    support=getattr(compiled,'support',compiled);ir=getattr(compiled,'ir',None)
    objects=(compiled,support) if ir is None else(compiled,support,ir)
    if any(getattr(o,n,None)for o in objects for n in('automatic_adjudications','consecutive_action_adjudications','declarations','repeated_cycle_target_conditions','no_progress_draw','aux_slots','triggers')):return limits
    if getattr(compiled,'repetition_policy',None)!='draw' or getattr(support,'repetition_policy',None)!='draw':return limits
    if getattr(compiled,'capture_disposition',None)!='remove_from_game' or getattr(compiled,'pass_enabled',False):return limits
    if any(h.total()for h in state.position.hands):return limits
    drops=getattr(support,'drop_allowed',{})
    if any(flag for owners in drops.values()for squares in owners for flag in squares):return limits
    for name in('promotion_allowed','promotion_forced'):
        if any(squares for owners in getattr(compiled,name,{}).values()for squares in owners):return limits
    types=getattr(compiled,'piece_types',())
    if not types or any(not isinstance(atom,LeapAtom)for t in types for atom in t.movement_atoms):return limits
    # Executable semantic movement, rather than legacy inspection metadata, wins.
    if ir is not None and any(g.kind not in('leap','drop')for g in ir.geometry.values()):return limits
    clock=getattr(compiled,'max_ply',None)
    if type(clock)is not int or clock!=getattr(support,'max_ply',None):return limits
    remaining=clock-state.ply_count
    requested=64 if limits.max_depth is None else limits.max_depth
    if state.terminal_status.is_terminal or not 0<remaining<requested:return limits
    return replace(limits,max_depth=remaining)
