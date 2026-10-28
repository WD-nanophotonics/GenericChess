"""Strict research admission for matching ordinary empty/capture Leap geometry.

The existing hash guard proves transition footprint only. This additional
consumer contract compares both executable pattern classes with the retained
metadata tables, typed support and owner frames. No legality pruning or proof
of full generic-domain execution, history, WDL or evaluator adequacy follows.
"""
from dataclasses import fields
from generic_chess.rules.ir import CompiledSemanticSupport,SemanticTypeMetadata
from generic_chess.core.search_runtime import _plain_leaper_hash_patterns
from generic_chess.core.movement import LeapAtom

def ordinary_leap_geometry(compiled,checkpoint=None):
    c=compiled
    if c is None or _plain_leaper_hash_patterns(c) is None:return None
    if checkpoint:checkpoint()
    shape=c.board_shape;types=c.types_by_id;support=c.support
    if shape.area>64 or len(types)>8 or not types or support is None:return None
    reviewed_support='board_size ruleset_fingerprint initial_position initial_setup_options type_metadata drop_allowed promotion_allowed promotion_forced empty_mobility repetition_limit repetition_policy max_ply stalemate_result automatic_adjudications board_width board_height pass_enabled consecutive_action_adjudications no_progress_draw'.split()
    if {f.name for f in fields(CompiledSemanticSupport)}!=set(reviewed_support):return None
    if {f.name for f in fields(SemanticTypeMetadata)}!={'type_id','is_anchor','is_promotable','promotion_target_ids'}:return None
    if not c.ir.capabilities.new_ir_core_executable:return None
    if support.board_shape!=shape or support.pass_enabled or support.no_progress_draw is not None:return None
    if support.automatic_adjudications or support.consecutive_action_adjudications:return None
    if any(any(any(row) for row in owners) for owners in support.drop_allowed.values()):return None
    if any(any(owners) for owners in support.promotion_allowed.values()) or any(any(owners) for owners in support.promotion_forced.values()):return None
    if support.ruleset_fingerprint!=c.ruleset_fingerprint or c.ir.ruleset_fingerprint!=c.ruleset_fingerprint or set(types)!=set(support.type_metadata):return None
    for tid,t in types.items():
        if any(not isinstance(a,LeapAtom) for a in t.movement_atoms) or t.is_anchor!=support.type_metadata[tid].is_anchor:return None
    actual={'target_empty':{},'target_enemy':{}}
    for p in c.ir.patterns:
        if checkpoint:checkpoint()
        if all(c.ir.geometry[g].kind=='drop' for g in p.geometry_ids):continue
        if p.target.kind not in actual:return None
        if len(p.invariants)!=1 or p.invariants[0].kind!='own_anchor_safe':return None
        for tid in p.type_ids:
            if tid not in types:return None
            for gid in p.geometry_ids:
                g=c.ir.geometry[gid]
                if g.kind!='leap':return None
                # A geometry associated with another actor is not this actor.
                if g.atom_source is not None and g.atom_source[0]!=tid:continue
                for owner in (0,1):
                    for src,path in g.paths.get(str(owner),{}).items():
                        if len(path)>1:return None
                        if path:actual[p.target.kind].setdefault((owner,tid,src),set()).add(path[0])
    result={}
    for tid,t in types.items():
        for owner in (0,1):
            for src in range(shape.area):
                if checkpoint:checkpoint()
                expected={s.rank*shape.width+s.file for s in c.empty_mobility[tid][owner][src]}
                key=(owner,tid,src)
                if any(actual[k].get(key,set())!=expected for k in actual):return None
                result[key]=frozenset(expected)
    return result
